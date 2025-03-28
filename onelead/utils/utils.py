import frappe
from frappe.utils.background_jobs import get_jobs

@frappe.whitelist()
def check_jobs_running():
    """
    Checks if any jobs with IDs starting with 'fetch_forms_' or 'fetch_campaigns_' are in 'queued' or 'started' status.
    Returns True if any such job is found; otherwise, returns False.
    """
    job_found = False
    queued_jobs = get_jobs(site=frappe.local.site, queue="long")

    print(queued_jobs.items())

    # Iterate through queued jobs in the "default" queue
    for job in queued_jobs.get(frappe.local.site, []):
        if "page_flow_fetch_page_and_campaign" in job:
            # if job_info.get("status") in ["queued", "started"]:
            job_found = True
            break  # Exit loop as soon as we find a matching job

    return job_found

@frappe.whitelist()
def get_lead_conversion_rate():
    # import json
    # from frappe.utils import getdate, nowdate

    # filters = json.loads(filters) if filters else {}

    # Interpret special date keywords
    # def normalize_date(val):
    #     if not val:
    #         return None
    #     if isinstance(val, str) and val.lower() in ["today", "now"]:
    #         return getdate(nowdate())
    #     return getdate(val)

    # from_date = normalize_date(filters.get("creation"))
    # to_date = normalize_date(filters.get("to_date"))
    # platform = filters.get("platform")

    # Build base filter conditions
    base_filters = {}
    # if platform:
    #     base_filters["platform"] = platform
    # if from_date or to_date:
    #     base_filters["creation"] = []
    #     if from_date:
    #         base_filters["creation"].append([">=", from_date])
    #     if to_date:
    #         base_filters["creation"].append(["<=", to_date])

    # Total records matching filters
    total = frappe.db.count("Meta Webhook Lead Logs", filters=base_filters)

    if total == 0:
        return {
            "value": 0,
            "fieldtype": "Percent"
        }

    # Add processing_status filter for converted leads
    converted_filters = base_filters.copy()
    converted_filters["processing_status"] = "Processed"

    converted = frappe.db.count("Meta Webhook Lead Logs", filters=converted_filters)

    rate = (converted / total) * 100
    print(rate)

    return {
        "value": round(rate, 2),
        "fieldtype": "Percent"
    }


# @frappe.whitelist()
# def get_lead_conversion_rate(filters=None):
#     import json
#     from frappe.utils import getdate

#     # Parse filters
#     filters = json.loads(filters) if filters else {}

#     conditions = []
#     values = {}

#     # Filter by creation date range
#     if filters.get("creation"):
#         conditions.append("creation >= %(from_date)s")
#         values["from_date"] = getdate(filters["creation"])

#     if filters.get("to_date"):
#         conditions.append("creation <= %(to_date)s")
#         values["to_date"] = getdate(filters["to_date"])

#     # Optional filter by platform
#     if filters.get("platform"):
#         conditions.append("platform = %(platform)s")
#         values["platform"] = filters["platform"]

#     # Build WHERE clause
#     where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

#     # Get total records
#     total = frappe.db.sql(
#         f"SELECT COUNT(*) FROM `tabMeta Webhook Lead Logs` {where_clause}",
#         values
#     )[0][0]

#     if total == 0:
#         return {
#             "value": 0,
#             "fieldtype": "Percent"
#         }

#     # Get processed records
#     processed = frappe.db.sql(
#         f"""
#         SELECT COUNT(*) FROM `tabMeta Webhook Lead Logs`
#         {where_clause} {'AND' if conditions else 'WHERE'} processing_status = 'Processed'
#         """,
#         values
#     )[0][0]

#     rate = (processed / total) * 100

#     return {
#         "value": round(rate, 2),
#         "fieldtype": "Percent"
#     }
