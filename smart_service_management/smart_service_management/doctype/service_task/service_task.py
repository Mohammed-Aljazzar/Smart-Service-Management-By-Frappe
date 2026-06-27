# Copyright (c) 2026, Mohammed Aljazzar and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate
from smart_service_management.smart_service_management.doctype.service_request.service_request import (
	create_notification,
	sync_service_request_metrics,
)


class ServiceTask(Document):
	def validate(self):
		self.validate_service_request()
		self.validate_dates()
		self.validate_hours()
		self.validate_completion_readiness()

	def after_insert(self):
		self.notify_assignee()

	def on_update(self):
		sync_service_request_metrics(self.service_request)

	def on_trash(self):
		sync_service_request_metrics(self.service_request)

	def validate_service_request(self):
		if not self.service_request:
			return

		request_status = frappe.db.get_value("Service Request", self.service_request, "status")
		if not request_status:
			frappe.throw(_("Service Request {0} does not exist.").format(frappe.bold(self.service_request)))

		if request_status in {"Rejected", "Closed"}:
			frappe.throw(
				_("Cannot create or update tasks for a service request with status {0}.").format(
					frappe.bold(request_status)
				)
			)

	def validate_dates(self):
		if self.start_date and self.deadline and getdate(self.deadline) < getdate(self.start_date):
			frappe.throw(_("Task deadline cannot be before the start date."))

	def validate_hours(self):
		if self.estimated_hours is not None and self.estimated_hours < 0:
			frappe.throw(_("Estimated hours cannot be negative."))

		if self.actual_hours is not None and self.actual_hours < 0:
			frappe.throw(_("Actual hours cannot be negative."))

	def validate_completion_readiness(self):
		if self.status == "Completed" and not self.actual_hours:
			frappe.throw(_("Actual hours are required before completing a service task."))

	def notify_assignee(self):
		if not self.assigned_to:
			return

		create_notification(
			self.assigned_to,
			_("Service Task Assigned: {0}").format(self.task_title),
			_("You are assigned to task {0} for service request {1}.").format(
				self.name,
				self.service_request,
			),
			reference_doctype=self.doctype,
			reference_name=self.name,
		)
