from smart_service_management.portal import get_enabled_services


no_cache = 1


def get_context(context):
	context.title = "Services"
	context.services = get_enabled_services()
