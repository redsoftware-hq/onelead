import frappe

def _get_jobs(site, queue):
    try:
        from frappe.utils.background_jobs import get_jobs
        return get_jobs(site=site, queue=queue)
    except ImportError:
        # Frappe v16: job introspection via RQ Job doctype
        jobs = frappe.get_all(
            "RQ Job",
            filters={"status": ["in", ["queued", "started"]]},
            fields=["job_id"],
        )
        return {site: [j.job_id for j in jobs]}

@frappe.whitelist()
def check_jobs_running():
    """
    Checks if any jobs with IDs starting with 'fetch_forms_' or 'fetch_campaigns_' are in 'queued' or 'started' status.
    Returns True if any such job is found; otherwise, returns False.
    """
    job_found = False
    queued_jobs = _get_jobs(site=frappe.local.site, queue="long")

    for job in queued_jobs.get(frappe.local.site, []):
        if "page_flow_fetch_page_and_campaign" in job:
            job_found = True
            break

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
