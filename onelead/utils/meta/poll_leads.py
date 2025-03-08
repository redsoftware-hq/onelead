import frappe
import json
import requests
from frappe.utils import now, get_datetime
from datetime import datetime, timedelta
from frappe.utils.background_jobs import enqueue_in
from .manage_ads import fetch_forms_based_on_page

def fetch_leads_for_form(form_id, access_token, last_poll_time, meta_config):
    """
    Fetch leads from Meta API for a specific Form ID, created after last_poll_time.
    """
    last_poll_epoch = int(get_datetime(last_poll_time).timestamp()) if last_poll_time else None
    url = f"{meta_config.meta_url}/{meta_config.meta_api_version}/{form_id}/leads"
    params = {"access_token": access_token, "fields": "id,created_time,field_data"}
    
    if last_poll_epoch:
        
        params["created_since"] = last_poll_epoch  # Only fetch leads after last poll

    response = requests.get(url, params=params)
    if response.status_code != 200:
        frappe.logger().error(f"Failed to fetch leads for Form {form_id}: {response.text}")
        return []

    return response.json().get("data", [])  # List of leads


def schedule_polling():
    """
    Dynamically schedule polling jobs based on polling_interval from Meta Webhook Config.
    """
    meta_config = frappe.get_single("Meta Webhook Config")

    if not meta_config.enable_polling:
        return

    polling_interval = meta_config.polling_interval or 15  # Default to 15 mins if not set

    # Ensure only one job is queued at a time
    job_name = "meta_polling_job"
    existing_job = frappe.utils.background_jobs.get_jobs(job_name=job_name)
    
    if not existing_job:
        enqueue_in(
            time_delta=timedelta(minutes=polling_interval),
            method="your_app.api.poll_meta_leads",
            queue="long",
            job_name=job_name
        )

def refresh_forms(pages=None):
    """
    Fetch the latest forms from Meta before polling.
    """
    if not pages:
        pages = frappe.get_all("Meta Ads Page Config", fields=["page"])
    for page in pages:
        page_id = page.get("page")
        if page_id:
            fetch_forms_based_on_page(page_id)  # Ensures latest forms are fetched


def get_active_forms_for_page(page_id):
    """
    Fetch Active Lead Forms from Meta Lead Form that belong to a given Page ID.
    """
    forms = frappe.get_all(
        "Meta Lead Form",
        filters={"page": page_id, "status": "ACTIVE"},
        fields=["form_id", "form_name"]
    )
    return forms

def fetch_and_process_leads(page_id, access_token, last_poll_time, meta_config, poll_log):
    """
    Fetch leads from all active forms under a Page & log them in Meta Webhook Lead Logs.
    """
    forms = get_active_forms_for_page(page_id)

    total_fetched = 0
    total_new = 0
    total_duplicates = 0
    total_failed = 0
    form_log_entries = []

    for form in forms:
        form_id = form.get("form_id")
        leads = fetch_leads_for_form(form_id, access_token, last_poll_time, meta_config)

        fetched = len(leads)
        total_fetched += fetched
        new_leads, duplicates, failed = process_leads(leads, form_id, page_id, poll_log)

        total_new += new_leads
        total_duplicates += duplicates
        total_failed += failed

        # Add form-wise summary
        form_log_entries.append({
            "lead_form": form_id,
            "leads_fetched": fetched,
            "new_leads_created": new_leads,
            "duplicate_leads": duplicates,
            "failed_leads": failed
        })

    return total_fetched, total_new, total_duplicates, total_failed, form_log_entries


def process_leads(leads, form_id, page_id, poll_log):
    """
    Process & store leads in Meta Webhook Lead Logs.
    """
    new_leads = 0
    duplicate_leads = 0
    failed_leads = 0

    for lead in leads:
        leadgen_id = lead.get("id")
        
        # Avoid duplicate leads
        if frappe.db.exists("Meta Webhook Lead Logs", {"leadgen_id": leadgen_id}):
            duplicate_leads += 1
            continue

        try:
            lead_log = frappe.new_doc("Meta Webhook Lead Logs")
            lead_log.update({
                "leadgen_id": leadgen_id,
                "page_id": page_id,
                "form_id": form_id,
                "raw_payload": json.dumps(lead),
                "lead_payload": json.dumps(lead),
                "received_time": now(),
                "created_time": lead.get("created_time"),
                "processing_status": "Pending",
                "source": "Polling",
                "polling_summary_log": poll_log.name  # Link lead to the polling job
            })
            lead_log.insert(ignore_permissions=True)
            new_leads += 1
        except Exception as e:
            failed_leads += 1
            frappe.logger().error(f"Failed to process lead {leadgen_id}: {str(e)}")

    return new_leads, duplicate_leads, failed_leads


@frappe.whitelist()
def poll_meta_leads():
    """
    Scheduled job that polls Meta API for leads across all pages.
    """
    poll_log = frappe.new_doc("Polling Summary Log")
    poll_log.job_start_time = now()
    poll_log.trigger_source = "Scheduled Cron Job"

    meta_config = frappe.get_single("Meta Webhook Config")
    if not meta_config.enable_polling:
        return

    last_poll_time = meta_config.last_polling_time
    meta_config.last_polling_time = now()
    meta_config.save(ignore_permissions=True)

    total_fetched = 0
    total_new = 0
    total_duplicates = 0
    total_failed = 0
    form_log_entries = []

    pages = frappe.get_all("Meta Ads Page Config", fields=["name", "page"])

    # Refresh Forms Before Polling
    refresh_forms(pages)
    
    for page in pages:
        page_id = page.get("page")  # Use "name" if "page" is unavailable
        access_token = meta_config.get_password("user_access_token")

        total_fetched, new_leads, duplicates, failed, form_logs = fetch_and_process_leads(
            page_id, access_token, last_poll_time, meta_config, poll_log
        )

        total_new += new_leads
        total_duplicates += duplicates
        total_failed += failed
        form_log_entries.extend(form_logs)

    poll_log.total_lead_fetched = total_fetched
    poll_log.new_leads_created = total_new
    poll_log.duplicate_leads = total_duplicates
    poll_log.failed_leads = total_failed
    poll_log.job_end_time = now()
    poll_log.polling_execution_time = (get_datetime(poll_log.job_end_time) - get_datetime(poll_log.job_start_time)).seconds

    # Attach form-wise breakdown
    for entry in form_log_entries:
        poll_log.append("form_details", entry)

    poll_log.insert(ignore_permissions=True)
    frappe.db.commit()

    # Schedule next polling run based on `polling_interval`
    schedule_polling()

    return f"Polling Complete: {total_new} New Leads, {total_duplicates} Duplicates, {total_failed} Failed."
