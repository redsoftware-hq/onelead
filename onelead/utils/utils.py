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
    # Define the statuses to include in total count
    relevant_statuses = ["Processed", "Error", "Loss"]
    # Total records matching filters
    total = frappe.db.count("Meta Webhook Lead Logs", 
                            filters={"processing_status": ["in", relevant_statuses]})

    if total == 0:
        return {
            "value": 0,
            "fieldtype": "Percent"
        }

    converted = frappe.db.count("Meta Webhook Lead Logs", filters={"processing_status": "Processed"})

    rate = (converted / total) * 100
    print(rate)

    return {
        "value": round(rate, 2),
        "fieldtype": "Percent"
    }
