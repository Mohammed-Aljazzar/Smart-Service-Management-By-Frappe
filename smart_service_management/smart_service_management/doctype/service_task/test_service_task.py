# Copyright (c) 2026, Mohammed Aljazzar and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today
from frappe.tests.utils import FrappeTestCase
from smart_service_management.smart_service_management.doctype.service_request.test_service_request import (
	make_service_request,
	move_service_request_through,
)


class TestServiceTask(FrappeTestCase):
	def test_rejects_deadline_before_start_date(self):
		request = make_service_request()
		doc = frappe.get_doc(
			{
				"doctype": "Service Task",
				"service_request": request.name,
				"task_title": "Deadline validation task",
				"assigned_to": "Administrator",
				"start_date": add_days(today(), 3),
				"deadline": add_days(today(), 1),
			}
		)

		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_rejects_task_for_closed_request(self):
		request = make_service_request()
		move_service_request_through(request, ["Pending Review", "Approved", "In Progress", "Completed", "Closed"])

		doc = frappe.get_doc(
			{
				"doctype": "Service Task",
				"service_request": request.name,
				"task_title": "Closed request task",
				"assigned_to": "Administrator",
				"start_date": today(),
				"deadline": add_days(today(), 1),
			}
		)

		self.assertRaises(frappe.ValidationError, doc.insert)
