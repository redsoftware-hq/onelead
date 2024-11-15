import frappe
from frappe.utils.background_jobs import get_jobs

@frappe.whitelist()
def check_jobs_running():
    """
    Checks if any jobs with IDs starting with 'fetch_forms_' or 'fetch_campaigns_' are in 'queued' or 'started' status.
    Returns True if any such job is found; otherwise, returns False.
    """
    job_found = False
    queued_jobs = get_jobs(site=frappe.local.site, queue="default")

    print(queued_jobs.items())

    # Iterate through queued jobs in the "default" queue
    for job in queued_jobs.get(frappe.local.site, []):
        if "fetch_campaigns" in job or "fetch_forms_based_on_page" in job:
            # if job_info.get("status") in ["queued", "started"]:
            job_found = True
            break  # Exit loop as soon as we find a matching job

    return job_found