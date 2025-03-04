import frappe
import json
import requests
from frappe.utils import now
from datetime import datetime
from werkzeug.wrappers import Response
import frappe.utils
import hashlib
import hmac
from frappe.utils.password import get_decrypted_password

@frappe.whitelist(allow_guest=True)
def webhook():
    """ Meta Ads Webhook Entry Point """
    if frappe.request.method == "GET":
        return validate()
    elif frappe.request.method == "POST":
        return leadgen()

def validate():
    """ Validate webhook token for initial connection setup """
    try:
        hub_challenge = frappe.form_dict.get("hub.challenge")
        verify_token = frappe.db.get_single_value("Meta Webhook Config", "webhook_verify_token")
        if frappe.form_dict.get("hub.verify_token") != verify_token:
            frappe.throw("Verify token does not match")
        return Response(hub_challenge, status=200)
    except Exception as e:
        frappe.logger().error(f"Webhook validation error: {str(e)}", exc_info=True)
        return Response(f"Error in webhook validation: {str(e)}", status=500)


def verify_signature(signature, payload, secret):
    """Verify the payload signature using HMAC SHA256"""
    if not signature:
        return False

    # Ensure signature starts with "sha256=" as expected
    if not signature.startswith("sha256="):
        return False

    # Compute HMAC SHA256
    computed_hash = hmac.new(
        bytes(secret, 'utf-8'),
        msg=bytes(payload, 'utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()

    # Compare computed signature with the one from headers
    return hmac.compare_digest(signature.split("=")[1], computed_hash)

def leadgen():
    """ Process lead data from Meta Ads webhook """
    try:
        data = frappe.request.json
        frappe.logger().info(f"Received POST request body: {json.dumps(data)}")

        # Validate payload with app secret
        conf = frappe.get_doc("Meta Webhook Config")
        app_secret = get_decrypted_password("Meta Webhook Config", conf.name, "app_secret")
        # app_secret = frappe.db.get_single_value("Meta Webhook Config", "app_secret")
        signature = frappe.request.headers.get("X-Hub-Signature-256")

        # check if  developemnt mode is enabled then skip signature verification
        if not frappe.conf.developer_mode:
            if not verify_signature(signature, json.dumps(data), app_secret):
                frappe.logger().error("Invalid signature. Payload verification failed.")
                return Response("Invalid signature", status=403)

        # Log incoming payload
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "leadgen":
                    lead_data = change.get("value")
                    leadgen_id = lead_data.get("leadgen_id")

                    # Check for duplicates
                    if frappe.db.exists("Meta Webhook Lead Logs", {"leadgen_id": leadgen_id}):
                        frappe.logger().info(f"Duplicate leadgen_id detected: {leadgen_id}")
                        continue
                    
                    # log entry
                    create_lead_log(data, lead_data, conf)

        return Response("Lead Logged", status=200)
    except Exception as e:
        frappe.logger().error(f"Error in Logging lead: {str(e)}", exc_info=True)
        return Response(f"Error: {str(e)}", status=500)


def create_lead_log(data, lead_data, global_conf):
    """Create a log entry for the incoming lead"""
    leadgen_id = lead_data.get("leadgen_id")
    page_id = lead_data.get("page_id")
    form_id = lead_data.get("form_id")
    ad_id = lead_data.get("ad_id")
    created_time = lead_data.get("created_time")

    lead_log = frappe.new_doc("Meta Webhook Lead Logs")
    lead_log.update({
        "raw_payload": json.dumps(data),
        "received_time": now(),
        "leadgen_id": leadgen_id,
        "page_id": page_id,
        "source": "Webhook",
        "ad_id": ad_id,
        "form_id": form_id,
        "Source": 'Webhook',
        "created_time": convert_epoch_to_frappe_date(created_time),
        "processing_status": "Pending"
    })

    configured_form = frappe.db.exists("Meta Lead Form", {"form_id": form_id})
    config = get_lead_config(page_id, form_id, global_conf)
    lead_log.config_doctype_name = "Meta Ads Page Config" if global_conf.page_flow else "Meta Ads Webhook Config"


    if configured_form:
        form_doc = frappe.get_doc("Meta Lead Form", {"form_id": form_id})
        lead_log.lead_doctype = form_doc.lead_doctype_reference
        lead_log.lead_form = form_id
        # 1a. remove form_doc.campaign for M:M relationship
        # if form_doc.campaign:
        #     lead_log.campaign = form_doc.campaign
        # 1a. add form_doc.ads for M:M relationship
        # if form_doc.ads:
        #     lead_log.ad = form_doc.ads
        if not lead_log.lead_doctype:
            lead_log.processing_status = "Unconfigured"
            lead_log.error_message = "No `Lead Doctype Reference` found in 'Meta Lead Form'"
    else:
        lead_log.processing_status = "Unconfigured"
        lead_log.error_message = f"No form found in `Meta Lead Form` for form_id: {lead_log.form_id}, please fetch forms again to get the latest forms."
        return
    
    if config:
        lead_log.config_reference = config.name
        if not config.get('enable'):
            lead_log.config_not_enabled = True
        if config.get('campaign', None):
            lead_log.campaign = config.campaign
    else:
        lead_log.processing_status = "Unconfigured"
        lead_log.error_message = ("No configuration found for form_id in 'Meta Lead Form'" if not configured_form else "No configuration found for page_id and form_id in 'Meta Ads Webhook Config'")

    lead_log.insert(ignore_permissions=True)


def get_lead_config(page_id, form_id, global_conf):
    """ Retrieve lead configuration based on page_id (and optionally form_id) in Meta Ads Webhook Config """
    filters = {"page": page_id}
    doctype_name = "Meta Ads Page Config" if global_conf.page_flow else "Meta Ads Webhook Config"
    
    config_list = frappe.get_all(doctype_name, filters=filters)

    if config_list:
        for config in config_list:
            config_doc = frappe.get_doc(doctype_name, config.name)

            # Ensure the form exists in the config's forms list
            form_exists = any(form.meta_lead_form == form_id for form in config_doc.forms_list)
            # frappe.logger().info(f"Form Exists in Config {config_doc.name}? {form_exists}")

            if form_exists:
                return config_doc  # Return config if found

    return None  # No configuration found for the page_id and form_id

def convert_epoch_to_frappe_date(epoch_time):
    """Convert epoch time to Frappe's date-time format."""
    # Convert epoch time to a datetime object
    dt = datetime.fromtimestamp(epoch_time)
    # Format the datetime object to Frappe's preferred format
    frappe_date = dt.strftime('%Y-%m-%d %H:%M:%S')
    return frappe_date
