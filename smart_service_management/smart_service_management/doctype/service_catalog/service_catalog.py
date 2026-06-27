# Copyright (c) 2026, Mohammed Aljazzar and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ServiceCatalog(Document):
	def validate(self):
		self.validate_pricing()
		self.validate_sla()
		self.validate_task_templates()

	def validate_pricing(self):
		if self.default_price is not None and self.default_price < 0:
			frappe.throw(_("Default price cannot be negative."))

		if self.default_estimated_hours is not None and self.default_estimated_hours < 0:
			frappe.throw(_("Default estimated hours cannot be negative."))

	def validate_sla(self):
		if self.default_sla_days is not None and self.default_sla_days < 1:
			frappe.throw(_("Default SLA days must be at least 1."))

	def validate_task_templates(self):
		seen_titles = set()
		for row in self.task_templates:
			if row.task_title in seen_titles:
				frappe.throw(_("Task template {0} is duplicated.").format(frappe.bold(row.task_title)))
			seen_titles.add(row.task_title)

			if row.estimated_hours is not None and row.estimated_hours < 0:
				frappe.throw(_("Estimated hours cannot be negative in task template {0}.").format(row.task_title))

			if row.due_after_days is not None and row.due_after_days < 0:
				frappe.throw(_("Due after days cannot be negative in task template {0}.").format(row.task_title))
