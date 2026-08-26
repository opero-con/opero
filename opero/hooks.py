app_name = "opero"

from opero import __version__ as _opero_asset_v

fixtures = [
	{
		"dt": "Custom Field",
		"filters": [
			[
				"name",
				"in",
				[
					"Project-zoho_project_id",
					"Timesheet Detail-zoho_entry_id",
					"Timesheet Detail-zoho_task_id",
				],
			]
		],
	},
]
app_title = "Opero"
app_publisher = "Patrick Willy"
app_description = "Custom development app for Opero"
app_email = "kakoi@hi2.in"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "opero",
# 		"logo": "/assets/opero/logo.png",
# 		"title": "Opero Custom Development",
# 		"route": "/opero",
# 		"has_permission": "opero.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# Query string busts desk asset caches when the app version advances.
app_include_css = f"/assets/opero/css/opero.css?v={_opero_asset_v}"
app_include_js = [
	f"/assets/opero/js/custom/resource_planner_reports.js?v={_opero_asset_v}",
	f"/assets/opero/js/custom/entity_scope.js?v={_opero_asset_v}",
]

# include js, css files in header of web template
# web_include_css = "/assets/opero/css/opero.css"
# web_include_js = "/assets/opero/js/opero.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "opero/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"ToDo": "public/js/todo.js",
	"Activity Cost": "public/js/custom/activity_cost.js",
	"Actual Spend": "public/js/custom/actual_spend.js",
	"Cash Advance-Reimbursable Form": "public/js/custom/cash_advance_reimbursable_form.js",
	"Consultant Task": "public/js/custom/consultant_task.js",
	"Item": "public/js/custom/item.js",
	"Leave Application": "public/js/custom/leave_application.js",
	"Material Request": "public/js/custom/material_request.js",
	"My ToDo": "public/js/custom/my_todo.js",
	"Project": "public/js/custom/project.js",
	"Project Budget": "public/js/custom/project_budget.js",
	"Project Time Allocation": "public/js/custom/project_time_allocation.js",
	"Task": "public/js/custom/task.js",
	"Task Time Distribution": "public/js/custom/task_time_distribution.js",
	"Timesheet": "public/js/custom/timesheet.js",
	"Travel Request": "public/js/custom/travel_request.js",
	"WASH Category": "public/js/custom/wash_category.js",
	"WASH Personnel": "public/js/custom/wash_personnel.js",
	"Work Hours Summary": "public/js/custom/work_hours_summary.js",
	"Opero Site Settings": "public/js/opero_site_settings.js",
	"Opero Site Publisher": "public/js/opero_site_publisher.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "opero/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "opero.utils.jinja_methods",
# 	"filters": "opero.utils.jinja_filters"
# }

# Boot
# ----

extend_bootinfo = "opero.boot.boot_session"

# Installation
# ------------

# before_install = "opero.install.before_install"
# after_install = "opero.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "opero.uninstall.before_uninstall"
# after_uninstall = "opero.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "opero.utils.before_app_install"
# after_app_install = "opero.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "opero.utils.before_app_uninstall"
# after_app_uninstall = "opero.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "opero.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

permission_query_conditions = {
	"ToDo": "opero.todo_enhancements.get_permission_query_conditions",
}

has_permission = {
	"ToDo": "opero.todo_enhancements.has_permission",
}

doc_events = {
	# Entity scoping: a Project's company owns every document beneath it.
	# Which DocTypes are scoped is data, held in opero/entity.py, so this is
	# wired once for all of them instead of being duplicated per DocType here.
	"*": {
		"validate": "opero.entity.apply_entity_scope",
	},
	"ToDo": {
		"validate": "opero.todo_enhancements.validate_todo",
		"on_update": "opero.todo_enhancements.on_update_todo",
	},
	"Timesheet": {
		"validate": "opero.events.timesheet.validate_timesheet",
		"before_submit": "opero.events.timesheet.before_submit_timesheet",
		"on_submit": "opero.zoho_books.sync_timesheet_to_zoho",
		"on_cancel": "opero.zoho_books.sync_timesheet_to_zoho",
		"on_amend": "opero.zoho_books.sync_timesheet_to_zoho",
	},
	"Task": {
		"before_insert": "opero.events.task.before_insert_task",
		"after_insert": "opero.events.task.after_insert_task",
		"on_update": "opero.events.task.on_update_task",
	},
	"Travel Request": {
		"validate": "opero.events.travel_request.validate_travel_request",
	},
	"HR Settings": {
		"on_update": "opero.events.hr_settings.on_update_hr_settings",
	},
	"Comment": {
		"on_update": "opero.events.comment.on_update_comment",
	},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"opero.tasks.all"
# 	],
# 	"daily": [
# 		"opero.tasks.daily"
# 	],
# 	"hourly": [
# 		"opero.tasks.hourly"
# 	],
# 	"weekly": [
# 		"opero.tasks.weekly"
# 	],
# 	"monthly": [
# 		"opero.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "opero.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "opero.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "opero.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["opero.utils.before_request"]
# after_request = ["opero.utils.after_request"]

# Job Events
# ----------
# before_job = ["opero.utils.before_job"]
# after_job = ["opero.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"opero.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
