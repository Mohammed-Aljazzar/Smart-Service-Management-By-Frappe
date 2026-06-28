import frappe
from frappe import _
from frappe.utils import add_days, flt, today


def get_enabled_services():
	return frappe.get_all(
		"Service Catalog",
		filters={"enabled": 1},
		fields=[
			"name",
			"service_name",
			"service_type",
			"default_price",
			"default_sla_days",
			"default_priority",
			"description",
		],
		order_by="service_name asc",
	)


@frappe.whitelist(allow_guest=True)
def create_customer_service_request(
	service_catalog,
	description,
	customer=None,
	customer_name=None,
	email=None,
	whatsapp_number=None,
	preferred_service_date=None,
):
	if not service_catalog or not frappe.db.exists("Service Catalog", service_catalog):
		frappe.throw(_("Please select a valid service."))

	catalog = frappe.get_doc("Service Catalog", service_catalog)
	if not catalog.enabled:
		frappe.throw(_("Service {0} is disabled.").format(frappe.bold(service_catalog)))

	customer = customer or get_or_create_portal_customer(customer_name, email)
	budget = flt(catalog.default_price) if catalog.default_price is not None else 100
	if budget < 100:
		budget = 100

	doc = frappe.get_doc({
		"doctype": "Service Request",
		"customer": customer,
		"service_catalog": catalog.name,
		"service_type": catalog.service_type,
		"description": description,
		"budget": budget,
		"priority": catalog.default_priority or "Medium",
		"assigned_to": catalog.default_assigned_to,
		"whatsapp_number": whatsapp_number,
		"preferred_service_date": preferred_service_date,
		"expected_delivery_date": add_days(today(), catalog.default_sla_days or 5),
		"status": "Draft",
	})
	doc.insert(ignore_permissions=True)

	return {
		"name": doc.name,
		"status": doc.status,
	}


def get_or_create_portal_customer(customer_name=None, email=None):
	if frappe.session.user != "Guest":
		contact_customer = get_customer_for_user(frappe.session.user)
		if contact_customer:
			return contact_customer

	customer_name = (customer_name or "").strip()
	email = (email or "").strip()
	if not customer_name:
		frappe.throw(_("Customer name is required."))

	if email:
		existing = frappe.db.get_value("Customer", {"email_id": email}, "name")
		if existing:
			return existing

	if frappe.db.exists("Customer", customer_name):
		return customer_name

	customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
	territory = frappe.db.get_value("Territory", {"is_group": 0}, "name")

	customer = frappe.get_doc({
		"doctype": "Customer",
		"customer_name": customer_name,
		"customer_type": "Individual",
		"customer_group": customer_group,
		"territory": territory,
		"email_id": email,
	})
	customer.insert(ignore_permissions=True)
	return customer.name


def get_customer_for_user(user):
	contact = frappe.db.get_value("Contact", {"user": user}, "name")
	if not contact:
		return None

	return frappe.db.get_value(
		"Dynamic Link",
		{
			"parenttype": "Contact",
			"parent": contact,
			"link_doctype": "Customer",
		},
		"link_name",
	)
