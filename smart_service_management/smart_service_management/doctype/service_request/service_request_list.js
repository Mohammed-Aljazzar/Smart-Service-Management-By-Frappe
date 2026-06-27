frappe.listview_settings["Service Request"] = {
	add_fields: ["status", "priority", "sla_status", "expected_delivery_date", "progress_percent"],
	get_indicator: function(doc) {
		const status_colors = {
			"Draft": "gray",
			"Pending Review": "orange",
			"Approved": "blue",
			"In Progress": "purple",
			"Completed": "green",
			"Closed": "darkgrey",
			"Rejected": "red",
		};

		return [__(doc.status), status_colors[doc.status] || "gray", `status,=,${doc.status}`];
	},
	onload: function(listview) {
		listview.page.add_inner_button(__("Service Request Report"), function() {
			frappe.set_route("query-report", "Service Request Report");
		});
	},
};
