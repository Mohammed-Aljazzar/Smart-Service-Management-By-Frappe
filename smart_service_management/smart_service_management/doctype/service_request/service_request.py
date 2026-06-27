# Copyright (c) 2026, Mohammed Aljazzar and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, flt, getdate, now_datetime, today


class ServiceRequest(Document):
	sla_days_by_priority = {
		"Urgent": 1,
		"High": 2,
		"Medium": 5,
		"Low": 14,
	}

	allowed_status_transitions = {
		"Draft": {"Pending Review"},
		"Pending Review": {"Approved", "Rejected"},
		"Approved": {"In Progress"},
		"In Progress": {"Completed"},
		"Completed": {"Closed"},
		"Closed": set(),
		"Rejected": set(),
	}

	def validate(self):
		self.capture_previous_values()
		self.apply_service_catalog_defaults()
		self.set_assignment_status()
		self.set_sla_due_date()
		self.set_sla_status()
		self.set_status_timestamps()
		self.set_task_metrics()
		self.validate_budget()
		self.validate_dates()
		self.validate_estimated_hours()
		self.validate_status_transition()
		self.record_status_change()
		self.validate_completion_readiness()

	def after_insert(self):
		self.notify_created()
		self.notify_assignment()

	def on_update(self):
		if self.flags.get("status_changed"):
			self.notify_status_change()
		if self.flags.get("assignment_changed"):
			self.notify_assignment()

	def capture_previous_values(self):
		self.flags.previous_status = None
		self.flags.previous_assigned_to = None

		if self.is_new():
			return

		values = frappe.db.get_value(
			self.doctype,
			self.name,
			["status", "assigned_to"],
			as_dict=True,
			cache=False,
		)
		if values:
			self.flags.previous_status = values.status
			self.flags.previous_assigned_to = values.assigned_to

	def apply_service_catalog_defaults(self):
		if not self.service_catalog:
			return

		catalog = get_service_catalog_defaults(self.service_catalog)
		if not catalog.get("enabled"):
			frappe.throw(_("Service {0} is disabled.").format(frappe.bold(self.service_catalog)))

		self.service_type = catalog.get("service_type") or self.service_type
		self.priority = self.priority or catalog.get("default_priority") or "Medium"

		if self.budget is None and catalog.get("default_price") is not None:
			self.budget = catalog.get("default_price")

		if self.estimated_hours is None and catalog.get("default_estimated_hours") is not None:
			self.estimated_hours = catalog.get("default_estimated_hours")

		if not self.description and catalog.get("description"):
			self.description = catalog.get("description")

		if not self.assigned_to and catalog.get("default_assigned_to"):
			self.assigned_to = catalog.get("default_assigned_to")

	def set_assignment_status(self):
		self.assignment_status = "Assigned" if self.assigned_to else "Unassigned"
		self.flags.assignment_changed = (
			not self.is_new()
			and self.flags.get("previous_assigned_to") != self.assigned_to
		)

	def set_sla_due_date(self):
		if self.expected_delivery_date:
			self.sla_due_date = self.expected_delivery_date
			return

		if self.service_catalog:
			days = frappe.db.get_value("Service Catalog", self.service_catalog, "default_sla_days")
		else:
			days = None

		days = days or self.sla_days_by_priority.get(self.priority or "Medium", 5)
		self.sla_due_date = add_days(today(), days)
		self.expected_delivery_date = self.sla_due_date

	def set_sla_status(self):
		if not self.sla_due_date:
			self.sla_status = "Not Set"
			self.days_overdue = 0
			return

		due_date = getdate(self.sla_due_date)
		reference_date = getdate(self.completed_on or today())

		if self.status in {"Completed", "Closed"}:
			if reference_date > due_date:
				self.sla_status = "Breached"
				self.days_overdue = date_diff(reference_date, due_date)
			else:
				self.sla_status = "Met"
				self.days_overdue = 0
			return

		if due_date < getdate(today()):
			self.sla_status = "Overdue"
			self.days_overdue = date_diff(today(), self.sla_due_date)
		elif due_date == getdate(today()):
			self.sla_status = "Due Today"
			self.days_overdue = 0
		else:
			self.sla_status = "On Track"
			self.days_overdue = 0

	def set_status_timestamps(self):
		if self.is_new():
			return

		previous_status = self.flags.get("previous_status") or frappe.db.get_value(
			self.doctype,
			self.name,
			"status",
			cache=False,
		)
		if not previous_status or previous_status == self.status:
			return

		if self.status == "In Progress" and not self.actual_start_date:
			self.actual_start_date = today()
		elif self.status == "Completed" and not self.completed_on:
			self.completed_on = today()
		elif self.status == "Closed" and not self.closed_on:
			self.closed_on = today()

	def set_task_metrics(self):
		if self.is_new():
			self.total_tasks = 0
			self.completed_tasks = 0
			self.open_tasks = 0
			self.overdue_tasks = 0
			self.progress_percent = 0
			self.actual_hours = 0
			return

		metrics = get_task_metrics(self.name)
		self.total_tasks = metrics["total_tasks"]
		self.completed_tasks = metrics["completed_tasks"]
		self.open_tasks = metrics["open_tasks"]
		self.overdue_tasks = metrics["overdue_tasks"]
		self.progress_percent = metrics["progress_percent"]
		self.actual_hours = metrics["actual_hours"]

	def validate_budget(self):
		if self.budget is not None and self.budget < 100:
			frappe.throw(_("Budget must be at least 100."))

	def validate_dates(self):
		if self.expected_delivery_date and getdate(self.expected_delivery_date) < getdate(today()):
			frappe.throw(_("Expected delivery date cannot be in the past."))

	def validate_estimated_hours(self):
		if self.estimated_hours is not None and self.estimated_hours < 0:
			frappe.throw(_("Estimated hours cannot be negative."))

	def validate_status_transition(self):
		if self.is_new():
			if not self.status:
				self.status = "Draft"
			if self.status != "Draft":
				frappe.throw(_("New service requests must start as Draft."))
			return

		previous_status = self.flags.get("previous_status") or frappe.db.get_value(
			self.doctype,
			self.name,
			"status",
			cache=False,
		)
		if not previous_status or previous_status == self.status:
			return

		allowed_next_statuses = self.allowed_status_transitions.get(previous_status, set())
		if self.status not in allowed_next_statuses:
			frappe.throw(
				_("{0} cannot move from {1} to {2}. Allowed next status: {3}.").format(
					frappe.bold("Service Request"),
					frappe.bold(previous_status),
					frappe.bold(self.status),
					frappe.bold(", ".join(sorted(allowed_next_statuses)) or _("None")),
				)
			)

		self.flags.status_changed = True

	def record_status_change(self):
		if self.is_new():
			if not self.status_history:
				self.append("status_history", {
					"from_status": "",
					"to_status": self.status or "Draft",
					"changed_by": frappe.session.user,
					"changed_on": now_datetime(),
					"note": _("Request created"),
				})
			return

		previous_status = self.flags.get("previous_status") or frappe.db.get_value(
			self.doctype,
			self.name,
			"status",
			cache=False,
		)
		if not previous_status or previous_status == self.status:
			return

		self.append("status_history", {
			"from_status": previous_status,
			"to_status": self.status,
			"changed_by": frappe.session.user,
			"changed_on": now_datetime(),
			"note": self.internal_notes if self.status == "Rejected" else "",
		})

	def validate_completion_readiness(self):
		if self.status not in {"Completed", "Closed"}:
			return

		if self.open_tasks:
			frappe.throw(
				_("Cannot mark this service request as {0} while {1} task(s) are still open.").format(
					frappe.bold(self.status), frappe.bold(self.open_tasks)
				)
			)

		if self.status == "Closed" and self.total_tasks and not flt(self.actual_hours):
			frappe.throw(_("Cannot close this service request before recording actual hours on its tasks."))

	def notify_created(self):
		notify_role_users(
			"Manager",
			_("New Service Request {0}").format(self.name),
			_("A new service request was created for {0}.").format(self.customer),
			reference_doctype=self.doctype,
			reference_name=self.name,
		)

	def notify_assignment(self):
		if not self.assigned_to:
			return

		create_notification(
			self.assigned_to,
			_("Service Request Assigned: {0}").format(self.name),
			_("You are assigned to service request {0} for {1}.").format(self.name, self.customer),
			reference_doctype=self.doctype,
			reference_name=self.name,
		)

	def notify_status_change(self):
		subject = _("Service Request {0} moved to {1}").format(self.name, self.status)
		message = _("Service request {0} for {1} is now {2}.").format(
			self.name,
			self.customer,
			self.status,
		)

		recipients = get_manager_users()
		if self.assigned_to:
			recipients.append(self.assigned_to)

		for user in sorted(set(recipients)):
			create_notification(
				user,
				subject,
				message,
				reference_doctype=self.doctype,
				reference_name=self.name,
			)


@frappe.whitelist()
def change_status(service_request, status, reason=None):
	doc = frappe.get_doc("Service Request", service_request)
	doc.check_permission("write")

	if status not in doc.allowed_status_transitions:
		frappe.throw(_("Unknown service request status {0}.").format(frappe.bold(status)))

	if status == "Rejected" and not reason:
		frappe.throw(_("Rejection reason is required."))

	if reason:
		doc.internal_notes = reason

	doc.status = status
	doc.save()

	return {
		"name": doc.name,
		"status": doc.status,
	}


@frappe.whitelist()
def get_service_overview(service_request):
	doc = frappe.get_doc("Service Request", service_request)
	doc.check_permission("read")

	metrics = get_task_metrics(service_request)
	feedback = frappe.db.get_value(
		"Service Feedback",
		{"service_request": service_request},
		["name", "rating", "feedback_date"],
		as_dict=True,
	)

	return {
		**metrics,
		"feedback": feedback,
		"sla_due_date": doc.sla_due_date,
		"sla_status": doc.sla_status,
		"days_overdue": doc.days_overdue,
		"expected_delivery_date": doc.expected_delivery_date,
		"status": doc.status,
		"assigned_to": doc.assigned_to,
		"assignment_status": doc.assignment_status,
	}


@frappe.whitelist()
def create_task(service_request, assigned_to, task_title=None):
	request = frappe.get_doc("Service Request", service_request)
	request.check_permission("write")

	if request.status in {"Rejected", "Closed"}:
		frappe.throw(_("Cannot create tasks for a service request with status {0}.").format(request.status))

	task = frappe.get_doc(
		{
			"doctype": "Service Task",
			"service_request": request.name,
			"task_title": task_title or _("Follow up on {0}").format(request.name),
			"assigned_to": assigned_to,
			"start_date": today(),
			"deadline": request.expected_delivery_date or request.sla_due_date,
			"status": "Open",
		}
	)
	task.insert()
	sync_service_request_metrics(request.name)

	return {
		"name": task.name,
		"doctype": task.doctype,
	}


@frappe.whitelist()
def create_tasks_from_template(service_request):
	request = frappe.get_doc("Service Request", service_request)
	request.check_permission("write")

	if not request.service_catalog:
		frappe.throw(_("Select a service before creating template tasks."))

	if request.status in {"Rejected", "Closed"}:
		frappe.throw(_("Cannot create tasks for a service request with status {0}.").format(request.status))

	catalog = frappe.get_doc("Service Catalog", request.service_catalog)
	if not catalog.enabled:
		frappe.throw(_("Service {0} is disabled.").format(frappe.bold(catalog.name)))

	created_tasks = []
	skipped_tasks = []
	for row in catalog.task_templates:
		if frappe.db.exists("Service Task", {"service_request": request.name, "task_title": row.task_title}):
			skipped_tasks.append(row.task_title)
			continue

		task = frappe.get_doc(
			{
				"doctype": "Service Task",
				"service_request": request.name,
				"task_title": row.task_title,
				"assigned_to": row.default_assigned_to or catalog.default_assigned_to or frappe.session.user,
				"start_date": today(),
				"deadline": add_days(today(), row.due_after_days or catalog.default_sla_days or 1),
				"estimated_hours": row.estimated_hours,
				"status": "Open",
			}
		)
		task.insert()
		created_tasks.append(task.name)

	if not created_tasks:
		return {
			"created": [],
			"skipped": skipped_tasks,
			"message": _("All template tasks already exist for this request."),
		}

	sync_service_request_metrics(request.name)
	return {
		"created": created_tasks,
		"skipped": skipped_tasks,
		"message": _("{0} template task(s) created.").format(len(created_tasks)),
	}


@frappe.whitelist()
def get_service_catalog_defaults(service_catalog):
	catalog = frappe.get_doc("Service Catalog", service_catalog)
	catalog.check_permission("read")

	return {
		"name": catalog.name,
		"enabled": catalog.enabled,
		"service_type": catalog.service_type,
		"default_priority": catalog.default_priority,
		"default_price": catalog.default_price,
		"default_sla_days": catalog.default_sla_days,
		"default_estimated_hours": catalog.default_estimated_hours,
		"default_assigned_to": catalog.default_assigned_to,
		"description": catalog.description,
		"task_count": len(catalog.task_templates or []),
	}


def get_task_metrics(service_request):
	total_tasks = frappe.db.count("Service Task", {"service_request": service_request})
	completed_tasks = frappe.db.count(
		"Service Task",
		{
			"service_request": service_request,
			"status": ["in", ["Completed", "Cancelled"]],
		},
	)
	open_tasks = frappe.db.count(
		"Service Task",
		{
			"service_request": service_request,
			"status": ["not in", ["Completed", "Cancelled"]],
		},
	)
	overdue_tasks = frappe.db.count(
		"Service Task",
		{
			"service_request": service_request,
			"status": ["not in", ["Completed", "Cancelled"]],
			"deadline": ["<", today()],
		},
	)
	hours = frappe.db.get_all(
		"Service Task",
		filters={"service_request": service_request},
		fields=["sum(actual_hours) as actual_hours"],
	)
	progress_percent = (completed_tasks / total_tasks * 100) if total_tasks else 0

	return {
		"total_tasks": total_tasks,
		"completed_tasks": completed_tasks,
		"open_tasks": open_tasks,
		"overdue_tasks": overdue_tasks,
		"progress_percent": progress_percent,
		"actual_hours": flt(hours[0].actual_hours) if hours else 0,
	}


def sync_service_request_metrics(service_request):
	if not service_request or not frappe.db.exists("Service Request", service_request):
		return

	metrics = get_task_metrics(service_request)
	frappe.db.set_value(
		"Service Request",
		service_request,
		{
			"total_tasks": metrics["total_tasks"],
			"completed_tasks": metrics["completed_tasks"],
			"open_tasks": metrics["open_tasks"],
			"overdue_tasks": metrics["overdue_tasks"],
			"progress_percent": metrics["progress_percent"],
			"actual_hours": metrics["actual_hours"],
		},
		update_modified=False,
	)


def get_manager_users():
	return [
		user.name
		for user in frappe.get_all(
			"Has Role",
			filters={
				"role": "Manager",
				"parenttype": "User",
			},
			fields=["parent as name"],
			distinct=True,
		)
		if frappe.db.get_value("User", user.name, "enabled")
	]


def notify_role_users(role, subject, message, reference_doctype=None, reference_name=None):
	users = frappe.get_all(
		"Has Role",
		filters={
			"role": role,
			"parenttype": "User",
		},
		fields=["parent as name"],
		distinct=True,
	)

	for user in users:
		if frappe.db.get_value("User", user.name, "enabled"):
			create_notification(
				user.name,
				subject,
				message,
				reference_doctype=reference_doctype,
				reference_name=reference_name,
			)


def create_notification(user, subject, message, reference_doctype=None, reference_name=None):
	if not user or not frappe.db.exists("User", user):
		return

	notification = frappe.new_doc("Notification Log")
	notification.update({
		"subject": subject,
		"type": "Alert",
		"for_user": user,
		"from_user": frappe.session.user if frappe.session.user != "Guest" else "Administrator",
		"email_content": message,
		"document_type": reference_doctype,
		"document_name": reference_name,
	})
	notification.insert(ignore_permissions=True)


def send_sla_notifications():
	"""Daily scheduler: notify assignees and managers about due or overdue service requests."""
	active_statuses = ["Draft", "Pending Review", "Approved", "In Progress"]
	requests = frappe.get_all(
		"Service Request",
		filters={
			"status": ["in", active_statuses],
			"sla_due_date": ["<=", add_days(today(), 1)],
		},
		fields=[
			"name",
			"customer",
			"status",
			"assigned_to",
			"sla_due_date",
			"days_overdue",
			"sla_status",
		],
		limit_page_length=0,
	)

	manager_users = get_manager_users()
	for request in requests:
		due_date = getdate(request.sla_due_date)
		if due_date < getdate(today()):
			subject = _("Overdue Service Request: {0}").format(request.name)
			message = _("Service request {0} for {1} is overdue since {2}.").format(
				request.name,
				request.customer,
				request.sla_due_date,
			)
		else:
			subject = _("Service Request Due Soon: {0}").format(request.name)
			message = _("Service request {0} for {1} is due on {2}.").format(
				request.name,
				request.customer,
				request.sla_due_date,
			)

		recipients = list(manager_users)
		if request.assigned_to:
			recipients.append(request.assigned_to)

		for user in sorted(set(recipients)):
			create_notification(
				user,
				subject,
				message,
				reference_doctype="Service Request",
				reference_name=request.name,
			)
