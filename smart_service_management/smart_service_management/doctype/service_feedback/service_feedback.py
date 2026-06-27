# Copyright (c) 2026, Mohammed Aljazzar and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, today
from frappe.model.document import Document


class ServiceFeedback(Document):
	def validate(self):
		self.set_customer_from_service_request()
		self.validate_service_request_status()
		self.validate_feedback_date()
		self.validate_duplicate_feedback()

	def set_customer_from_service_request(self):
		if not self.service_request:
			return

		customer = frappe.db.get_value("Service Request", self.service_request, "customer")
		if not customer:
			frappe.throw(_("Service Request {0} does not exist.").format(frappe.bold(self.service_request)))

		if self.customer and self.customer != customer:
			frappe.throw(_("Feedback customer must match the customer on the service request."))

		self.customer = customer

	def validate_service_request_status(self):
		if not self.service_request:
			return

		request_status = frappe.db.get_value("Service Request", self.service_request, "status")
		if request_status not in {"Completed", "Closed"}:
			frappe.throw(_("Feedback can only be added for completed or closed service requests."))

	def validate_feedback_date(self):
		if self.feedback_date and getdate(self.feedback_date) > getdate(today()):
			frappe.throw(_("Feedback date cannot be in the future."))

	def validate_duplicate_feedback(self):
		if not self.service_request:
			return

		existing_feedback = frappe.db.exists(
			"Service Feedback",
			{
				"service_request": self.service_request,
				"name": ["!=", self.name],
			},
		)
		if existing_feedback:
			frappe.throw(_("Only one feedback entry is allowed per service request."))
