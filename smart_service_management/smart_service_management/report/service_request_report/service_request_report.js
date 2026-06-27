frappe.query_reports["Service Request Report"] = {
	filters: [
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "service_catalog",
			label: __("Service"),
			fieldtype: "Link",
			options: "Service Catalog",
		},
		{
			fieldname: "service_type",
			label: __("Service Type"),
			fieldtype: "Select",
			options: "\nDesign\nDevelopment\nMarketing\nConsulting\nTraining",
		},
		{
			fieldname: "priority",
			label: __("Priority"),
			fieldtype: "Select",
			options: "\nLow\nMedium\nHigh\nUrgent",
		},
		{
			fieldname: "assigned_to",
			label: __("Assigned To"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "assignment_status",
			label: __("Assignment Status"),
			fieldtype: "Select",
			options: "\nUnassigned\nAssigned",
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nPending Review\nApproved\nIn Progress\nCompleted\nClosed\nRejected",
		},
		{
			fieldname: "sla_status",
			label: __("SLA Status"),
			fieldtype: "Select",
			options: "\nOn Track\nDue Today\nOverdue\nMet\nBreached\nNot Set",
		},
		{
			fieldname: "from_date",
			label: __("Expected From"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("Expected To"),
			fieldtype: "Date",
		},
		{
			fieldname: "overdue_only",
			label: __("Overdue Only"),
			fieldtype: "Check",
		},
	],
};
