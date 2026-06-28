# Smart Service Management

[![Frappe](https://img.shields.io/badge/Frappe-App-0089FF)](https://frappeframework.com)
[![ERPNext](https://img.shields.io/badge/ERPNext-Ready-5E64FF)](https://erpnext.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](license.txt)

Smart Service Management is a Frappe / ERPNext app for running service operations from request intake to task execution, SLA monitoring, customer feedback, and billing.

It gives teams a clean Desk workflow for managers and employees, plus a customer-facing service request page that can turn website interest into structured ERPNext records.

## Highlights

- Public services page for customers: `/services`
- Service catalog with default price, SLA, priority, assignee, task templates, and billing item
- Service request lifecycle: Draft -> Pending Review -> Approved -> In Progress -> Completed -> Closed
- Task generation from service templates
- SLA due dates, overdue tracking, progress metrics, and daily reminders
- One-click Sales Invoice creation from completed or closed service requests
- WhatsApp status message shortcut from the request form
- Customer feedback with automatic follow-up for low ratings
- Workspace cards, shortcuts, and a script report for daily operations

## Quick Links

Replace `training.localhost:8000` with your site domain and port.

| Area | URL |
| --- | --- |
| Customer services page | [Open `/services`](http://training.localhost:8000/services) |
| Desk app | [Open Desk](http://training.localhost:8000/app) |
| Smart Service Management workspace | [Open workspace](http://training.localhost:8000/app/smart-service-management) |
| Service Request list | [Open Service Requests](http://training.localhost:8000/app/service-request) |
| Service Catalog list | [Open Service Catalog](http://training.localhost:8000/app/service-catalog) |
| Service Task list | [Open Service Tasks](http://training.localhost:8000/app/service-task) |
| Service Feedback list | [Open Service Feedback](http://training.localhost:8000/app/service-feedback) |
| Service Request Report | [Open report](http://training.localhost:8000/app/query-report/Service%20Request%20Report) |

## GitHub

- Repository: [Mohammed-Aljazzar/Smart-Service-Management-By-Frappe](https://github.com/Mohammed-Aljazzar/Smart-Service-Management-By-Frappe)
- Service portal code: [`smart_service_management/portal.py`](smart_service_management/portal.py)
- Website page: [`smart_service_management/www/services.html`](smart_service_management/www/services.html)
- Service Request controller: [`service_request.py`](smart_service_management/smart_service_management/doctype/service_request/service_request.py)
- Service Request client script: [`service_request.js`](smart_service_management/smart_service_management/doctype/service_request/service_request.js)
- Service Request Report: [`service_request_report.py`](smart_service_management/smart_service_management/report/service_request_report/service_request_report.py)

## Core Workflow

1. Create services in **Service Catalog** with default SLA, price, priority, assignee, and task templates.
2. Customers or staff create a **Service Request**.
3. Managers review the request and move it to **Approved** or **Rejected**.
4. Approved requests move to **In Progress**.
5. Teams create tasks manually or from the service template.
6. Progress, actual hours, overdue tasks, and SLA status update on the request.
7. Completed requests can generate a linked **Sales Invoice**.
8. Customers submit **Service Feedback** after completion or closure.
9. Low ratings automatically create manager notifications and follow-up ToDos.

## Main DocTypes

### Service Catalog

Defines the services your team offers.

Key fields:

- Service Name
- Service Type
- Default Price
- Billing Item
- Default SLA Days
- Default Estimated Hours
- Default Assigned To
- Task Templates

### Service Request

The main operational document for each customer request.

Key capabilities:

- Status-controlled lifecycle
- SLA due date and status
- Assignment status
- Preferred service date
- WhatsApp number
- Task progress metrics
- Linked Sales Invoice
- Status history

### Service Task

Tracks execution work under a service request.

Key capabilities:

- Assigned employee
- Start date and deadline
- Estimated and actual hours
- Open, In Progress, Completed, and Cancelled states
- Automatic sync back to the parent request

### Service Feedback

Captures the customer experience after completion.

Key capabilities:

- One feedback entry per request
- Rating and comment
- Auto-filled customer
- Manager follow-up for ratings below 3

## Website Portal

The `/services` page lists enabled services and includes a request form.

The form can collect:

- Selected service
- Customer name
- Email
- WhatsApp number
- Preferred date
- Request details

When submitted, it creates a **Service Request** in Draft status and uses the selected service defaults for price, SLA, priority, and assignee.

## Billing

Completed or closed service requests can create a **Sales Invoice** directly from the form.

The invoice uses:

- The request customer
- The selected service billing item, when configured
- The request budget as the invoice rate
- The default company, income account, and cost center from ERPNext

The request is updated with:

- Sales Invoice link
- Billing Status = Invoiced

## Reporting

The **Service Request Report** helps managers track the operation from one place.

It includes:

- Customer
- Service
- Priority
- Assigned user
- Request status
- SLA status
- Preferred date
- Expected delivery date
- Overdue days
- Progress percentage
- Open and overdue tasks
- Actual hours
- Budget
- Billing status
- Linked Sales Invoice
- Next action

Useful filters include status, SLA status, assigned user, billing status, date range, and overdue-only.

## Installation

From your bench directory:

```bash
bench get-app https://github.com/Mohammed-Aljazzar/Smart-Service-Management-By-Frappe.git
bench --site your-site.localhost install-app smart_service_management
bench --site your-site.localhost migrate
bench --site your-site.localhost clear-cache
```

For an existing local checkout:

```bash
cd /path/to/frappe-bench
bench --site your-site.localhost migrate
bench --site your-site.localhost clear-cache
```

## Development

```bash
cd apps/smart_service_management
pre-commit install
```

Run targeted checks:

```bash
python3 -m compileall -q smart_service_management
python3 -m json.tool smart_service_management/smart_service_management/doctype/service_request/service_request.json
python3 -m json.tool smart_service_management/smart_service_management/doctype/service_catalog/service_catalog.json
```

Run app tests:

```bash
bench --site your-site.localhost run-tests --app smart_service_management
```

## Runtime Verification

After installing or updating the app:

1. Open `/services` and submit a service request.
2. Confirm the new record appears in **Service Request**.
3. Move the request through the workflow using the form buttons.
4. Create template tasks from the request.
5. Complete tasks and confirm progress updates.
6. Mark the request Completed.
7. Create a Sales Invoice from the request.
8. Add feedback and test that ratings below 3 notify managers.
9. Open **Service Request Report** and filter by Billing Status or Overdue Only.

## Scheduler

The app includes a daily scheduler event for SLA notifications:

```python
smart_service_management.smart_service_management.doctype.service_request.service_request.send_sla_notifications
```

It notifies managers and assignees about due-soon and overdue service requests.

## Recommended Setup

Before using the app in production, configure:

- Default Company
- Income Account
- Cost Center
- Service Catalog records
- Billing Item for each billable service
- Manager and Employee roles
- Website domain and portal access
- Email / Notification settings

## License

MIT
