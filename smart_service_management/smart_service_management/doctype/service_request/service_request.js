// service_request.js
// Client Script لـ Service Request
// هذا الكود ينفذ في متصفح المستخدم

frappe.ui.form.on('Service Request', {
    
    /**
     * onload: تُستدعى عند تحميل النموذج (فتح الصفحة)
     */
    onload: function(frm) {
        console.log('📄 تم تحميل نموذج Service Request');
        
        // جعل حقل الحالة للقراءة فقط (لا يمكن تعديله يدوياً)
        frm.set_df_property('status', 'read_only', 1);
        
        // عند تغيير الأولوية → نحدث تاريخ التسليم
        frm.fields_dict['priority'].df.onchange = function() {
            frm.trigger('update_delivery_date');
        };
    },
    
    /**
     * refresh: تُستدعى عند تحديث النموذج (بعد كل حفظ أو فتح)
     */
    refresh: function(frm) {
        console.log('🔄 تحديث النموذج - الحالة:', frm.doc.status);
        
        // 1. تلوين الحالة في أعلى الصفحة
        colorizeStatus(frm);
        
        // 2. إضافة أزرار مخصصة حسب الحالة
        if (!frm.is_new()) {
            loadServiceOverview(frm);
            addCustomButtons(frm);
            addRelatedButtons(frm);
        }
    },
    
    /**
     * update_delivery_date: عند تغيير الأولوية
     */
    update_delivery_date: function(frm) {
        let days = 7; // افتراضي
        
        if (frm.doc.priority === 'Urgent') {
            days = 1;
            frappe.show_alert({
                message: '⚡ أولوية عاجلة! التسليم خلال يوم واحد',
                indicator: 'red'
            });
        } else if (frm.doc.priority === 'High') {
            days = 2;
            frappe.show_alert({
                message: '🔴 أولوية عالية! التسليم خلال يومين',
                indicator: 'orange'
            });
        } else if (frm.doc.priority === 'Medium') {
            days = 5;
        } else if (frm.doc.priority === 'Low') {
            days = 14;
        }
        
        // حساب تاريخ التسليم
        let delivery_date = frappe.datetime.add_days(
            frappe.datetime.nowdate(), days
        );
        frm.set_value('expected_delivery_date', delivery_date);
    },

    service_catalog: function(frm) {
        if (!frm.doc.service_catalog) {
            return;
        }

        frappe.call({
            method: 'smart_service_management.smart_service_management.doctype.service_request.service_request.get_service_catalog_defaults',
            args: {
                service_catalog: frm.doc.service_catalog
            },
            callback: function(r) {
                if (!r.message) {
                    return;
                }

                applyServiceDefaults(frm, r.message);
            }
        });
    },
    
    /**
     * validate: تُستدعى قبل حفظ النموذج (تحقق من البيانات)
     */
    validate: function(frm) {
        // 1. التحقق من الميزانية
        if (frm.doc.budget && frm.doc.budget < 100) {
            frappe.throw('❌ الميزانية يجب أن تكون أكثر من 100');
        }
        
        // 2. التحقق من تاريخ التسليم
        if (frm.doc.expected_delivery_date) {
            let today = frappe.datetime.nowdate();
            if (frm.doc.expected_delivery_date < today) {
                frappe.msgprint({
                    title: '⚠️ تنبيه',
                    message: 'تاريخ التسليم في الماضي! يرجى مراجعته.',
                    indicator: 'orange'
                });
            }
        }
    }
});

/**
 * دالة تلوين الحالة
 */
function colorizeStatus(frm) {
    let colors = {
        'Draft': 'gray',
        'Pending Review': 'yellow',
        'Approved': 'blue',
        'In Progress': 'purple',
        'Completed': 'green',
        'Closed': 'darkgray',
        'Rejected': 'red'
    };
    
    let color = colors[frm.doc.status] || 'gray';
    frm.page.set_indicator(frm.doc.status, color);
}

/**
 * دالة إضافة الأزرار المخصصة
 */
function addCustomButtons(frm) {
    
    // زر: إرسال للمراجعة (يظهر في حالة Draft)
    if (frm.doc.status === 'Draft') {
        frm.add_custom_button(
            '📤 إرسال للمراجعة',
            function() {
                changeStatus(frm, 'Pending Review');
            },
            'Actions'
        );
    }
    
    // زر: موافقة (يظهر في حالة Pending Review)
    if (frm.doc.status === 'Pending Review') {
        frm.add_custom_button(
            '✅ موافقة',
            function() {
                changeStatus(frm, 'Approved');
            },
            'Actions'
        );
        
        frm.add_custom_button(
            '❌ رفض',
            function() {
                frappe.prompt(
                    {
                        fieldname: 'reason',
                        fieldtype: 'Small Text',
                        label: 'سبب الرفض',
                        reqd: 1
                    },
                    function(values) {
                        changeStatus(frm, 'Rejected', values.reason);
                    },
                    'سبب الرفض'
                );
            },
            'Actions'
        );
    }
    
    // زر: بدء التنفيذ (يظهر في حالة Approved)
    if (frm.doc.status === 'Approved') {
        frm.add_custom_button(
            '🔄 بدء التنفيذ',
            function() {
                changeStatus(frm, 'In Progress');
            },
            'Actions'
        );
    }
    
    // زر: إكمال (يظهر في حالة In Progress)
    if (frm.doc.status === 'In Progress') {
        frm.add_custom_button(
            '🏁 إكمال',
            function() {
                changeStatus(frm, 'Completed');
            },
            'Actions'
        );
    }
    
    // زر: إغلاق (يظهر في حالة Completed)
    if (frm.doc.status === 'Completed') {
        frm.add_custom_button(
            '🔒 إغلاق',
            function() {
                changeStatus(frm, 'Closed');
            },
            'Actions'
        );
    }
}

/**
 * أزرار التشغيل اليومية للطلب
 */
function addRelatedButtons(frm) {
    frm.add_custom_button(
        'تقرير الطلبات',
        function() {
            frappe.set_route('query-report', 'Service Request Report', {
                customer: frm.doc.customer,
                status: frm.doc.status
            });
        },
        'Related'
    );

    frm.add_custom_button(
        'عرض المهام',
        function() {
            frappe.route_options = {
                service_request: frm.doc.name
            };
            frappe.set_route('List', 'Service Task');
        },
        'Related'
    );

    if (!['Rejected', 'Closed'].includes(frm.doc.status)) {
        frm.add_custom_button(
            'Assign to Me',
            function() {
                frm.set_value('assigned_to', frappe.session.user);
                frm.save();
            },
            'Related'
        );

        frm.add_custom_button(
            'إنشاء مهمة',
            function() {
                promptCreateTask(frm);
            },
            'Related'
        );

        if (frm.doc.service_catalog) {
            frm.add_custom_button(
                'إنشاء مهام القالب',
                function() {
                    createTemplateTasks(frm);
                },
                'Related'
            );
        }
    }

    if (['Completed', 'Closed'].includes(frm.doc.status)) {
        if (!frm.doc.sales_invoice) {
            frm.add_custom_button(
                'إنشاء فاتورة',
                function() {
                    createSalesInvoice(frm);
                },
                'Billing'
            );
        } else {
            frm.add_custom_button(
                'فتح الفاتورة',
                function() {
                    frappe.set_route('Form', 'Sales Invoice', frm.doc.sales_invoice);
                },
                'Billing'
            );
        }

        frm.add_custom_button(
            'إضافة تقييم',
            function() {
                frappe.new_doc('Service Feedback', {
                    service_request: frm.doc.name
                });
            },
            'Related'
        );
    }

    if (frm.doc.whatsapp_number) {
        frm.add_custom_button(
            'WhatsApp',
            function() {
                openWhatsAppStatusMessage(frm);
            },
            'Related'
        );
    }
}

function promptCreateTask(frm) {
    frappe.prompt(
        [
            {
                fieldname: 'task_title',
                fieldtype: 'Data',
                label: 'عنوان المهمة',
                reqd: 1
            },
            {
                fieldname: 'assigned_to',
                fieldtype: 'Link',
                label: 'مسند إلى',
                options: 'User',
                default: frm.doc.assigned_to || frappe.session.user,
                reqd: 1
            }
        ],
        function(values) {
            frappe.call({
                method: 'smart_service_management.smart_service_management.doctype.service_request.service_request.create_task',
                args: {
                    service_request: frm.doc.name,
                    task_title: values.task_title,
                    assigned_to: values.assigned_to
                },
                freeze: true,
                freeze_message: 'جاري إنشاء المهمة...',
                callback: function(r) {
                    frm.reload_doc();
                    if (r.message && r.message.name) {
                        frappe.set_route('Form', 'Service Task', r.message.name);
                    }
                }
            });
        },
        'إنشاء مهمة خدمة'
    );
}

function loadServiceOverview(frm) {
    frappe.call({
        method: 'smart_service_management.smart_service_management.doctype.service_request.service_request.get_service_overview',
        args: {
            service_request: frm.doc.name
        },
        callback: function(r) {
            if (r.message) {
                renderServiceOverview(frm, r.message);
            }
        }
    });
}

function renderServiceOverview(frm, overview) {
    let feedbackText = overview.feedback
        ? `${overview.feedback.rating || 0}/5`
        : 'لا يوجد';
    let slaText = overview.sla_status || 'Not Set';
    let overdueText = overview.days_overdue
        ? `${overview.days_overdue} يوم`
        : '-';
    let assignedText = overview.assigned_to || 'Unassigned';

    let html = `
        <div class="row">
            <div class="col-sm-3"><b>المهام</b><br>${overview.completed_tasks}/${overview.total_tasks}</div>
            <div class="col-sm-3"><b>مهام مفتوحة / متأخرة</b><br>${overview.open_tasks} / ${overview.overdue_tasks || 0}</div>
            <div class="col-sm-3"><b>التقدم / الساعات</b><br>${Math.round(overview.progress_percent || 0)}% / ${overview.actual_hours || 0}</div>
            <div class="col-sm-3"><b>SLA</b><br>${slaText} (${overdueText})</div>
        </div>
        <div class="row" style="margin-top: 12px;">
            <div class="col-sm-3"><b>التقييم</b><br>${feedbackText}</div>
            <div class="col-sm-3"><b>Assigned To</b><br>${assignedText}</div>
        </div>
    `;

    frm.dashboard.add_section(html, __('Service Overview'));
    frm.dashboard.show();
}

function applyServiceDefaults(frm, service) {
    if (!service.enabled) {
        frappe.msgprint({
            title: 'الخدمة غير مفعلة',
            message: 'هذه الخدمة غير مفعلة ولا يمكن استخدامها للطلبات الجديدة.',
            indicator: 'red'
        });
        return;
    }

    frm.set_value('service_type', service.service_type);
    frm.set_value('priority', service.default_priority || 'Medium');

    if (!frm.doc.budget && service.default_price !== null) {
        frm.set_value('budget', service.default_price);
    }

    if (!frm.doc.estimated_hours && service.default_estimated_hours !== null) {
        frm.set_value('estimated_hours', service.default_estimated_hours);
    }

    if (!frm.doc.assigned_to && service.default_assigned_to) {
        frm.set_value('assigned_to', service.default_assigned_to);
    }

    if (!frm.doc.description && service.description) {
        frm.set_value('description', service.description);
    }

    if (!frm.doc.expected_delivery_date && service.default_sla_days) {
        frm.set_value(
            'expected_delivery_date',
            frappe.datetime.add_days(frappe.datetime.nowdate(), service.default_sla_days)
        );
    }

    if (service.task_count) {
        frappe.show_alert({
            message: `${service.task_count} مهمة قالبية جاهزة لهذه الخدمة`,
            indicator: 'blue'
        });
    }
}

function createTemplateTasks(frm) {
    frappe.call({
        method: 'smart_service_management.smart_service_management.doctype.service_request.service_request.create_tasks_from_template',
        args: {
            service_request: frm.doc.name
        },
        freeze: true,
        freeze_message: 'جاري إنشاء مهام القالب...',
        callback: function(r) {
            frm.reload_doc();
            let result = r.message || {};
            let createdCount = Array.isArray(result)
                ? result.length
                : (result.created || []).length;
            let message = result.message || `تم إنشاء ${createdCount} مهمة`;

            frappe.show_alert({
                message: message,
                indicator: createdCount ? 'green' : 'orange'
            });
        }
    });
}

function createSalesInvoice(frm) {
    frappe.confirm(
        'سيتم إنشاء Sales Invoice بقيمة الميزانية الحالية وربطها بهذا الطلب. هل تريد المتابعة؟',
        function() {
            frappe.call({
                method: 'smart_service_management.smart_service_management.doctype.service_request.service_request.create_sales_invoice',
                args: {
                    service_request: frm.doc.name
                },
                freeze: true,
                freeze_message: 'جاري إنشاء الفاتورة...',
                callback: function(r) {
                    frm.reload_doc();
                    if (r.message && r.message.name) {
                        frappe.show_alert({
                            message: r.message.already_exists ? 'الفاتورة موجودة مسبقاً' : 'تم إنشاء الفاتورة',
                            indicator: 'green'
                        });
                        frappe.set_route('Form', 'Sales Invoice', r.message.name);
                    }
                }
            });
        }
    );
}

function openWhatsAppStatusMessage(frm) {
    let number = (frm.doc.whatsapp_number || '').replace(/[^\d]/g, '');
    if (!number) {
        frappe.msgprint('رقم واتساب غير صالح.');
        return;
    }

    let message = [
        `مرحباً، تحديث على طلب الخدمة ${frm.doc.name}:`,
        `الحالة الحالية: ${frm.doc.status || '-'}`,
        `الخدمة: ${frm.doc.service_catalog || '-'}`,
        `موعد التسليم المتوقع: ${frm.doc.expected_delivery_date || '-'}`,
        `حالة SLA: ${frm.doc.sla_status || '-'}`
    ].join('\n');

    window.open(`https://wa.me/${number}?text=${encodeURIComponent(message)}`, '_blank');
}

/**
 * تغيير الحالة من السيرفر حتى تبقى قواعد العمل موحدة لكل طرق الاستخدام
 */
function changeStatus(frm, status, reason) {
    frappe.call({
        method: 'smart_service_management.smart_service_management.doctype.service_request.service_request.change_status',
        args: {
            service_request: frm.doc.name,
            status: status,
            reason: reason
        },
        freeze: true,
        freeze_message: 'جاري تحديث الحالة...',
        callback: function() {
            frm.reload_doc();
        }
    });
}
