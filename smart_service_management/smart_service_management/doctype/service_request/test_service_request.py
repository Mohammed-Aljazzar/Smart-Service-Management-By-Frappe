# Copyright (c) 2026, Mohammed Aljazzar and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today
from frappe.tests.utils import FrappeTestCase


def make_test_customer(customer_name="_Test Smart Service Customer"):
	if frappe.db.exists("Customer", customer_name):
		return customer_name

	customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
	territory = frappe.db.get_value("Territory", {"is_group": 0}, "name")

	frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": customer_name,
			"customer_type": "Individual",
			"customer_group": customer_group,
			"territory": territory,
		}
	).insert(ignore_permissions=True)

	return customer_name


def make_service_request(**kwargs):
	doc = frappe.get_doc(
		{
			"doctype": "Service Request",
			"customer": make_test_customer(),
			"service_type": "Development",
			"description": "Build a small service workflow.",
			"budget": 500,
			"priority": "Medium",
			"expected_delivery_date": add_days(today(), 5),
			**kwargs,
		}
	)
	doc.insert(ignore_permissions=True)
	doc.reload()
	return doc


def make_service_catalog(service_name="_Runtime Smart Service Package"):
	if frappe.db.exists("Service Catalog", service_name):
		return service_name

	doc = frappe.get_doc(
		{
			"doctype": "Service Catalog",
			"service_name": service_name,
			"enabled": 1,
			"service_type": "Development",
			"default_priority": "High",
			"default_price": 750,
			"default_sla_days": 3,
			"default_estimated_hours": 12,
			"default_assigned_to": "Administrator",
			"description": "Runtime service catalog validation package.",
			"task_templates": [
				{
					"task_title": "Discovery",
					"default_assigned_to": "Administrator",
					"estimated_hours": 2,
					"due_after_days": 1,
				},
				{
					"task_title": "Delivery",
					"default_assigned_to": "Administrator",
					"estimated_hours": 10,
					"due_after_days": 3,
				},
			],
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def move_service_request_through(request, statuses):
	change_status = frappe.get_attr(
		"smart_service_management.smart_service_management.doctype.service_request.service_request.change_status"
	)

	for status in statuses:
		change_status(request.name, status)
		request.reload()

	return request


def run_runtime_validation():
	results = []

	def expect_validation(label, action):
		try:
			action()
		except frappe.ValidationError:
			results.append(label)
		else:
			frappe.throw(f"{label} did not raise ValidationError")

	try:
		expect_validation(
			"low budget blocked",
			lambda: frappe.get_doc(
				{
					"doctype": "Service Request",
					"customer": make_test_customer("_Runtime SSM Customer"),
					"service_type": "Development",
					"description": "Runtime low budget test.",
					"budget": 50,
					"priority": "Medium",
					"expected_delivery_date": add_days(today(), 3),
				}
			).insert(ignore_permissions=True),
		)

		request = make_service_request(customer=make_test_customer("_Runtime SSM Customer"))
		request.status = "Approved"
		expect_validation("invalid status transition blocked", request.save)

		request = make_service_request(customer=make_test_customer("_Runtime SSM Customer Action"))
		change_status = frappe.get_attr(
			"smart_service_management.smart_service_management.doctype.service_request.service_request.change_status"
		)
		change_status(request.name, "Pending Review")
		request.reload()
		if request.status != "Pending Review":
			frappe.throw("Server-side status action did not update the service request.")
		results.append("server-side status action works")

		create_task = frappe.get_attr(
			"smart_service_management.smart_service_management.doctype.service_request.service_request.create_task"
		)
		task_result = create_task(request.name, "Administrator", "Runtime generated task")
		if not task_result.get("name"):
			frappe.throw("Server-side task action did not create a task.")
		request.reload()
		if request.total_tasks != 1 or request.open_tasks != 1:
			frappe.throw("Service request task metrics were not updated after task creation.")
		results.append("server-side task action updates progress metrics")

		move_service_request_through(request, ["Approved", "In Progress"])
		expect_validation("completion with open task blocked", lambda: change_status(request.name, "Completed"))

		catalog_name = make_service_catalog()
		catalog_request = frappe.get_doc(
			{
				"doctype": "Service Request",
				"customer": make_test_customer("_Runtime SSM Catalog Customer"),
				"service_catalog": catalog_name,
			}
		)
		catalog_request.insert(ignore_permissions=True)
		if catalog_request.budget != 750 or catalog_request.estimated_hours != 12:
			frappe.throw("Service catalog defaults were not applied to the service request.")
		results.append("service catalog defaults applied")

		create_tasks_from_template = frappe.get_attr(
			"smart_service_management.smart_service_management.doctype.service_request.service_request.create_tasks_from_template"
		)
		created_tasks = create_tasks_from_template(catalog_request.name)
		if len(created_tasks.get("created", [])) != 2:
			frappe.throw("Service catalog task templates did not create the expected tasks.")
		catalog_request.reload()
		if catalog_request.total_tasks != 2 or catalog_request.open_tasks != 2:
			frappe.throw("Template task creation did not update service request metrics.")
		results.append("service catalog task templates created")

		request = make_service_request(customer=make_test_customer("_Runtime SSM Customer 2"))
		move_service_request_through(request, ["Pending Review", "Approved", "In Progress", "Completed", "Closed"])

		expect_validation(
			"task for closed request blocked",
			lambda: frappe.get_doc(
				{
					"doctype": "Service Task",
					"service_request": request.name,
					"task_title": "Closed request task should fail",
					"assigned_to": "Administrator",
					"start_date": today(),
					"deadline": add_days(today(), 1),
				}
			).insert(ignore_permissions=True),
		)

		request = make_service_request(customer=make_test_customer("_Runtime SSM Customer 3"))
		expect_validation(
			"early feedback blocked",
			lambda: frappe.get_doc(
				{
					"doctype": "Service Feedback",
					"service_request": request.name,
					"customer": request.customer,
					"rating": 5,
					"feedback_date": today(),
				}
			).insert(ignore_permissions=True),
		)

		move_service_request_through(request, ["Pending Review", "Approved", "In Progress", "Completed"])

		feedback = frappe.get_doc(
			{
				"doctype": "Service Feedback",
				"service_request": request.name,
				"rating": 5,
				"feedback_date": today(),
			}
		)
		feedback.insert(ignore_permissions=True)
		if feedback.customer != request.customer:
			frappe.throw("Feedback customer was not copied from the service request.")

		results.append("completed feedback accepted and customer auto-filled")
		return results
	finally:
		frappe.db.rollback()


class TestServiceRequest(FrappeTestCase):
	def test_rejects_low_budget(self):
		doc = frappe.get_doc(
			{
				"doctype": "Service Request",
				"customer": make_test_customer(),
				"service_type": "Development",
				"description": "Budget validation test.",
				"budget": 50,
				"priority": "Medium",
				"expected_delivery_date": add_days(today(), 5),
			}
		)

		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_rejects_invalid_status_transition(self):
		doc = make_service_request(customer=make_test_customer("_Test Invalid Transition Customer"))
		doc.reload()
		doc.status = "Approved"

		with self.assertRaises(frappe.ValidationError):
			doc.validate_status_transition()

	def test_allows_valid_status_transition(self):
		doc = make_service_request()
		move_service_request_through(doc, ["Pending Review"])

		self.assertEqual(doc.status, "Pending Review")
