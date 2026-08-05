app_name = "opero"

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
	{
		"dt": "Server Script",
		"filters": [
			[
				"name",
				"in",
				[
					"Allocated Hrs Fetch and Throw",
					"Anti Spill",
					"Auto Share Records",
					"Available Hrs",
					"Chart in Project Budget",
					"Custom_Title",
					"Full Name",
					"Get Project Master Managers",
					"Holidays Fetch",
					"Missing Project Rate Factor",
					"Non PM Restriction",
					"PM Email Fetch",
					"Previous Workflow State",
					"Sum of Allocated Hrs in Project",
					"TTD Update",
					"Time dist. listen to working hrs",
					"ToDo AutoShare upon Mention",
					"ToDo Email Notification",
					"on_update push to TTD",
					"on_update pust start to TDD",
				],
			]
		],
	},
]
app_title = "Opero Custom Development"
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
app_include_css = "/assets/opero/css/opero.css"
# app_include_js = "/assets/opero/js/opero.js"

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
	"Actual Spend": "public/js/custom/actual_spend.js",
	"Cash Advance-Reimbursable Form": "public/js/custom/cash_advance_reimbursable_form.js",
	"Consultant Task": "public/js/custom/consultant_task.js",
	"Material Request": "public/js/custom/material_request.js",
	"My ToDo": "public/js/custom/my_todo.js",
	"Project": "public/js/custom/project.js",
	"Project Budget": "public/js/custom/project_budget.js",
	"Project Time Allocation": "public/js/custom/project_time_allocation.js",
	"Task": "public/js/custom/task.js",
	"Task Time Distribution": "public/js/custom/task_time_distribution.js",
	"Timesheet": "public/js/custom/timesheet.js",
	"Travel Request": "public/js/custom/travel_request.js",
	"WaSH Category": "public/js/custom/wash_category.js",
	"WaSH Personnel": "public/js/custom/wash_personnel.js",
	"Work Hours Summary": "public/js/custom/work_hours_summary.js",
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
	"ToDo": {
		"validate": "opero.todo_enhancements.validate_todo",
	},
	"Timesheet": {
		"on_submit": "opero.zoho_books.sync_timesheet_to_zoho",
		"on_cancel": "opero.zoho_books.sync_timesheet_to_zoho",
		"on_amend": "opero.zoho_books.sync_timesheet_to_zoho",
	}
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
