import frappe


def after_install():
    create_onelead_manager_role()

def create_onelead_manager_role():
    role_name = "One Lead Manager"

    # Check if role exists
    if not frappe.db.exists("Role", role_name):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": role_name,
            "desk_access": 1,  # Enables access to Desk (important for routing)
        }).insert(ignore_permissions=True)
        frappe.db.commit()
