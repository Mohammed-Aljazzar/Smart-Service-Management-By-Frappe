# Copyright (c) 2026, Mohammed Aljazzar and Contributors
# See license.txt

import frappe
from frappe.utils import today
from frappe.tests.utils import FrappeTestCase
from smart_service_management.smart_service_management.doctype.service_request.test_service_request import (
	make_test_customer,
	make_service_request,
	move_service_request_through,
)


class TestServiceFeedback(FrappeTestCase):
	def test_rejects_feedback_before_request_is_completed(self):
		request = make_service_request()
		doc = frappe.get_doc(
			{
				"doctype": "Service Feedback",
				"service_request": request.name,
				"customer": request.customer,
				"rating": 5,
				"feedback_date": today(),
			}
		)

		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_sets_customer_from_service_request(self):
		request = make_service_request()
		move_service_request_through(request, ["Pending Review", "Approved", "In Progress", "Completed"])

		doc = frappe.get_doc(
			{
				"doctype": "Service Feedback",
				"service_request": request.name,
				"rating": 5,
				"feedback_date": today(),
			}
		)
		doc.insert(ignore_permissions=True)

		self.assertEqual(doc.customer, request.customer)

	def test_rejects_customer_mismatch(self):
		request = make_service_request()
		move_service_request_through(request, ["Pending Review", "Approved", "In Progress", "Completed"])

		doc = frappe.get_doc(
			{
				"doctype": "Service Feedback",
				"service_request": request.name,
				"customer": make_test_customer("_Test Other Smart Service Customer"),
				"rating": 5,
				"feedback_date": today(),
			}
		)

		self.assertRaises(frappe.ValidationError, doc.insert)
