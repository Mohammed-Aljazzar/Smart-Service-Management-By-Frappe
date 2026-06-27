# Copyright (c) 2026, Mohammed Aljazzar and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate, today


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	summary = get_summary(data)

	return columns, data, None, chart, summary


def get_columns():
	return [
		{
			"fieldname": "name",
			"label": _("Service Request"),
			"fieldtype": "Link",
			"options": "Service Request",
			"width": 160,
		},
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 180,
		},
		{
			"fieldname": "service_catalog",
			"label": _("Service"),
			"fieldtype": "Link",
			"options": "Service Catalog",
			"width": 170,
		},
		{
			"fieldname": "service_type",
			"label": _("Type"),
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"fieldname": "priority",
			"label": _("Priority"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "assigned_to",
			"label": _("Assigned To"),
			"fieldtype": "Link",
			"options": "User",
			"width": 150,
		},
		{
			"fieldname": "assignment_status",
			"label": _("Assignment"),
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"fieldname": "sla_status",
			"label": _("SLA"),
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"fieldname": "expected_delivery_date",
			"label": _("Expected Delivery"),
			"fieldtype": "Date",
			"width": 130,
		},
		{
			"fieldname": "days_overdue",
			"label": _("Days Overdue"),
			"fieldtype": "Int",
			"width": 115,
		},
		{
			"fieldname": "progress_percent",
			"label": _("Progress %"),
			"fieldtype": "Percent",
			"width": 110,
		},
		{
			"fieldname": "open_tasks",
			"label": _("Open Tasks"),
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"fieldname": "overdue_tasks",
			"label": _("Overdue Tasks"),
			"fieldtype": "Int",
			"width": 115,
		},
		{
			"fieldname": "actual_hours",
			"label": _("Actual Hours"),
			"fieldtype": "Float",
			"width": 110,
		},
		{
			"fieldname": "age_days",
			"label": _("Age Days"),
			"fieldtype": "Int",
			"width": 95,
		},
		{
			"fieldname": "resolution_days",
			"label": _("Resolution Days"),
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"fieldname": "budget",
			"label": _("Budget"),
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"fieldname": "next_action",
			"label": _("Next Action"),
			"fieldtype": "Data",
			"width": 190,
		},
	]


def get_data(filters):
	request_filters = build_filters(filters)

	rows = frappe.get_list(
		"Service Request",
		filters=request_filters,
		fields=[
			"name",
			"customer",
			"service_catalog",
			"service_type",
			"priority",
			"assigned_to",
			"assignment_status",
			"status",
			"sla_status",
			"expected_delivery_date",
			"sla_due_date",
			"days_overdue",
			"progress_percent",
			"total_tasks",
			"completed_tasks",
			"open_tasks",
			"overdue_tasks",
			"actual_hours",
			"budget",
			"creation",
			"completed_on",
			"closed_on",
		],
		order_by="expected_delivery_date asc, modified desc",
		limit_page_length=0,
	)

	enriched_rows = [enrich_row(row) for row in rows]
	if filters.get("overdue_only"):
		enriched_rows = [
			row for row in enriched_rows
			if row.status not in {"Completed", "Closed", "Rejected"} and flt(row.days_overdue) > 0
		]

	return enriched_rows


def build_filters(filters):
	request_filters = []

	for fieldname in (
		"customer",
		"service_catalog",
		"service_type",
		"priority",
		"assigned_to",
		"assignment_status",
		"status",
		"sla_status",
	):
		if filters.get(fieldname):
			request_filters.append([fieldname, "=", filters[fieldname]])

	if filters.get("from_date"):
		request_filters.append(["expected_delivery_date", ">=", filters["from_date"]])

	if filters.get("to_date"):
		request_filters.append(["expected_delivery_date", "<=", filters["to_date"]])

	if filters.get("overdue_only"):
		request_filters.extend([
			["status", "not in", ["Completed", "Closed", "Rejected"]],
			["expected_delivery_date", "<", today()],
		])

	return request_filters


def enrich_row(row):
	row = frappe._dict(row)
	row["next_action"] = get_next_action(row)
	row["age_days"] = date_diff(today(), getdate(row.creation))
	row["resolution_days"] = None

	if row.completed_on:
		row["resolution_days"] = date_diff(row.completed_on, getdate(row.creation))
	elif row.closed_on:
		row["resolution_days"] = date_diff(row.closed_on, getdate(row.creation))

	if row.expected_delivery_date and row.status not in {"Completed", "Closed", "Rejected"}:
		due_date = getdate(row.expected_delivery_date)
		if due_date < getdate(today()):
			row["days_overdue"] = max(row.days_overdue or 0, (getdate(today()) - due_date).days)
			row["sla_status"] = "Overdue"

	return row


def get_next_action(row):
	if row.status == "Draft":
		return _("Submit for review")
	if row.status == "Pending Review":
		return _("Approve or reject")
	if row.status == "Approved":
		return _("Start work")
	if row.status == "In Progress":
		if row.open_tasks:
			return _("Complete open tasks")
		return _("Mark completed")
	if row.status == "Completed":
		return _("Close or request feedback")
	if row.status == "Closed":
		return _("No action")
	if row.status == "Rejected":
		return _("Rejected")
	return _("Review")


def get_chart(data):
	status_counts = {}
	for row in data:
		status_counts[row.status] = status_counts.get(row.status, 0) + 1

	if not status_counts:
		return None

	labels = list(status_counts.keys())
	values = [status_counts[label] for label in labels]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Requests"), "values": values}],
		},
		"type": "donut",
	}


def get_summary(data):
	total = len(data)
	open_count = sum(1 for row in data if row.status not in {"Completed", "Closed", "Rejected"})
	overdue_count = sum(1 for row in data if row.sla_status in {"Overdue", "Breached"} or flt(row.days_overdue) > 0)
	completed_count = sum(1 for row in data if row.status in {"Completed", "Closed"})
	avg_progress = sum(flt(row.progress_percent) for row in data) / total if total else 0

	return [
		{
			"value": total,
			"label": _("Total Requests"),
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": open_count,
			"label": _("Active Requests"),
			"datatype": "Int",
			"indicator": "orange" if open_count else "green",
		},
		{
			"value": overdue_count,
			"label": _("Overdue / Breached"),
			"datatype": "Int",
			"indicator": "red" if overdue_count else "green",
		},
		{
			"value": completed_count,
			"label": _("Completed / Closed"),
			"datatype": "Int",
			"indicator": "green",
		},
		{
			"value": avg_progress,
			"label": _("Average Progress"),
			"datatype": "Percent",
			"indicator": "blue",
		},
	]
