from frappe import _


def get_data():
	return {
		"fieldname": "service_request",
		"transactions": [
			{
				"label": _("Delivery"),
				"items": ["Service Task"],
			},
			{
				"label": _("Quality"),
				"items": ["Service Feedback"],
			},
		],
	}
