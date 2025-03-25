app_name = "onelead"
app_title = "One Lead"
app_publisher = "Redsoftware Solutions"
app_description = "One app for featching all Ad Form Leads"
app_email = "dev@redsoftware.in"
app_license = "mit"
# required_apps = []


#  Allowed APIs
csrf_exempt = {
    "onelead.utils.meta_lead.webhook": True,
    "onelead.utils.google_lead.webhook": True
}

webhooks = [
    {"method": "POST", "path": "onelead.utils.meta_lead.webhook"},
    {"method": "GET", "path": "onelead.utils.meta_lead.webhook"},
    {"method": "POST", "path": "onelead.utils.google_lead.webhook"},
    {"method": "GET", "path": "onelead.utils.google_lead.webhook"}
]


doc_events = {
    "Meta Lead Form": {
        "before_save": "onelead.utils.meta.manage_ads.fetch_form_details"
    },
    "Meta Webhook Lead Logs": {
        "after_insert": "onelead.utils.meta.manage_leads.process_logged_lead"
    }
}

# Includes in <head>
# ------------------

app_include_css = "/assets/onelead/css/meta.css"

# include js, css files in header of desk.html
# app_include_css = "/assets/onelead/css/onelead.css"
# app_include_js = "/assets/onelead/js/onelead.js"

# include js, css files in header of web template
# web_include_css = "/assets/onelead/css/onelead.css"
# web_include_js = "/assets/onelead/js/onelead.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "onelead/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "onelead/public/icons.svg"

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
# 	"methods": "onelead.utils.jinja_methods",
# 	"filters": "onelead.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "onelead.install.before_install"
after_install = "onelead.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "onelead.uninstall.before_uninstall"
# after_uninstall = "onelead.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "onelead.utils.before_app_install"
# after_app_install = "onelead.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "onelead.utils.before_app_uninstall"
# after_app_uninstall = "onelead.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "onelead.notifications.get_notification_config"

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

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"onelead.tasks.all"
# 	],
# 	"daily": [
# 		"onelead.tasks.daily"
# 	],
# 	"hourly": [
# 		"onelead.tasks.hourly"
# 	],
# 	"weekly": [
# 		"onelead.tasks.weekly"
# 	],
# 	"monthly": [
# 		"onelead.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "onelead.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "onelead.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "onelead.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["onelead.utils.before_request"]
# after_request = ["onelead.utils.after_request"]

# Job Events
# ----------
# before_job = ["onelead.utils.before_job"]
# after_job = ["onelead.utils.after_job"]

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
# 	"onelead.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

