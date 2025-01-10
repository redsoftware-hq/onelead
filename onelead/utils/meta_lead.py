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
                frappe.logger().warning("Invalid signature. Payload verification failed.")
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
        "ad_id": ad_id,
        "form_id": form_id,
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
        if not lead_log.lead_doctype:
            lead_log.processing_status = "Unconfigured"
            lead_log.error_message = "No lead_doctype_reference found in 'Meta Lead Form'"

    if config:
        lead_log.config_reference = config.name
        if not config.get('enable'):
            lead_log.config_not_enabled = True
        if config.get('campaign', None):
            lead_log.campaign = config.campaign
    else:
        lead_log.processing_status = "Unconfigured"
        lead_log.error_message = ("No configuration found for form_id in 'Meta Lead Form'" 
                                  if not configured_form else 
                                  "No configuration found for page_id and form_id in 'Meta Ads Webhook Config'")

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


# def process_lead_changes(data, lead_log):
#   try:
#     if "entry" in data:
#       for entry in data["entry"]:
#         if "changes" in entry:
#           for change in entry["changes"]:
#             if change["field"] == "leadgen":
#               leadgen_id = change["value"].get("leadgen_id")              
#               # adgroup_id = change["value"].get("adgroup_id")
#               page_id = change["value"].get("page_id")

#               try:
#                 lead_exists = frappe.get_doc("Meta Lead Logs", f"{page_id}_{leadgen_id}")

#                 if lead_exists:
#                   frappe.logger().info(f"Lead with leadgen_id {leadgen_id} exists!")
#                   return
#               except:
#                 # New Lead entry, no lead found.
#                 pass
                
#               lead_log.set("leadgen_id", leadgen_id)
#               lead_log.set("page_id", page_id)
              
#               lead_conf = None 

#               # Only during testing there won't be any page_id. when hit from developer plateform webhook.
#               if page_id:
#                   filters = {}
#                   # if adgroup_id:
#                   #     filters['ad_group_id'] = adgroup_id
#                   if page_id:
#                       filters['page_id'] = page_id
              
#               lead_conf = frappe.get_all('Meta Ad Campaign Config', filters=filters, limit_page_length=1)

#               if lead_conf and len(lead_conf) > 0 and leadgen_id:

#                 # Call and fetch doc data again, to fetch all child table data as well.
#                 config = frappe.get_doc('Meta Ad Campaign Config', lead_conf[0]['name'])
#                 lead_log.set("meta_ads_config", config.name)
#                 lead_log.set("lead_doctype_reference", config.lead_doctype)

#                 lead_log.insert(ignore_permissions=True)

#                 frappe.logger().info(f"Lead configuration found for unique key: { page_id}")
#                 fetch_lead_data(leadgen_id, config, lead_log)
#               else:
#                 frappe.logger().error(f"No lead configuration found for unique key: { page_id}")

#   except Exception as e:
#     frappe.logger().error(f"Error in processing lead changes: {str(e)}", exc_info=True)
#     raise

# def fetch_lead_data(leadgen_id, lead_conf, lead_log):
#   try:
#     conf = frappe.get_doc("Meta Webhook Config")
#     url = f"{conf.meta_url}/{conf.meta_api_version}/{leadgen_id}/"

#     user_access_token = get_decrypted_password('Meta Ad Campaign Config', lead_conf.name, 'user_access_token')
#     # access_token = get_decrypted_password("Meta Webhook Config", conf.name, "access_token")
#     params = {"access_token": user_access_token}
#     frappe.logger().info(f"Fetching lead data from Meta API for leadgen_id: {leadgen_id}")
#     response = requests.get(url, params=params)

#     if response.status_code == 200:
#       frappe.logger().info(f"Successfully fetched lead data for leadgen_id: {leadgen_id}")
#       lead_data = response.json()
#       lead_log.set("lead_json", lead_data)
#       lead_log.save(ignore_permissions=True)

#       new_lead = process_lead_data(lead_data, lead_conf)
#       print(new_lead)
#       # lead_log.set("lead_doctype", new_lead.get("lead_name"))
#       lead_log.set("lead_entry_successful", True)
#       lead_log.save(ignore_permissions=True)

#       return new_lead
#     else:
#       frappe.logger().error(f"Failed to fetch lead data for leadgen_id: {leadgen_id}. Status Code: {response.status_code}, Response: {response.text}")
  
#   except requests.RequestException as e:
#     lead_log.set("error", f"Request error while fetching lead data: {str(e)}")
#     lead_log.save(ignore_permissions=True)
#     frappe.logger().error(f"Request error while fetching lead data: {str(e)}", exc_info=True)
#     raise
  
#   except Exception as e:
#     lead_log.set("error", f"Error in fetching lead data: {str(e)}")
#     lead_log.save(ignore_permissions=True)
#     frappe.logger().error(f"Error in fetching lead data: {str(e)}", exc_info=True)
#     raise

# def process_lead_data(lead_data, lead_conf):
#   try:
#     field_data = lead_data.get("field_data", [])
#     lead_doctype = lead_conf.get('lead_doctype')
#     new_lead = frappe.new_doc(lead_doctype)
#     wb_lead_info = {field["name"]: field["values"][0] for field in field_data}

#     frappe.logger().info(f"Processing lead data: {wb_lead_info}")
    
#     for mapping in lead_conf.mapping:
#       ad_form_key = mapping.ad_form_field_key
#       lead_doc_field = mapping.lead_doctype_field

#       if ad_form_key in wb_lead_info:
#         ad_form_value = wb_lead_info.get(ad_form_key)
#         if ad_form_key == "phone_number":
#           ad_form_value = formate_phone_number(wb_lead_info.get(ad_form_key))
#         new_lead.set(lead_doc_field, ad_form_value)

#     for constant in lead_conf.constants:
#       new_lead.set(constant.lead_doctype_field, constant.constant_value)

#     # if lead_conf.time_field:
#     #   new_lead.set(lead_conf.lead_doctype_time_field, format_epoch_time())

#     new_lead.insert(ignore_permissions=True)
#     frappe.db.commit()

#     frappe.logger().info(f"Lead created successfully with name: {new_lead.name}")
#     return {"message": "Lead created successfully", "lead_name": new_lead.name}
  
#   except Exception as e:
#     frappe.logger().error(f"Error in processing lead data: {str(e)}", exc_info=True)
#     raise

# def formate_phone_number(phone_number):
#     if phone_number and phone_number.startswith("+"):
#         phone_number = phone_number.replace(" ", "").replace("-", "")
#         return f"{phone_number[:3]}-{phone_number[3:]}"
#     else:
#         return phone_number

# def format_epoch_time(epoch_time):


# def process_lead_data(lead_data, lead_conf):
#   field_data = lead_data.get("field_data", [])
#   new_lead = frappe.new_doc(lead_conf.get('lead_doctype'))
#   wb_lead_info = {field["name"]: field["values"][0] for field in field_data}
#   print(wb_lead_info)
  
#   for mapping in lead_conf.mapping:
#     ad_form_key = mapping.ad_form_field_key
#     lead_doc_field = mapping.lead_doctype_field

#     if ad_form_key in wb_lead_info:
#       new_lead.set(lead_doc_field, wb_lead_info.get(ad_form_key))

#     for constant in lead_conf.constants:
#       new_lead.set(constant.lead_doctype_field, constant.constant_value)

#   new_lead.insert(ignore_permissions=True)
#   frappe.db.commit()
#   # # Format phone number if it contains a country code
#   # phone_number = wb_lead_info.get("phone_number")
#   # if phone_number and phone_number.startswith("+"):
#   #   phone_number = phone_number.replace(" ", "").replace("-", "")
#   #   formatted_phone_number = f"{phone_number[:3]}-{phone_number[3:]}"
#   # else:
#   #   formatted_phone_number = phone_number

#   # data = {
#   #   "doctype": "Leads",
#   #   "lead_name": wb_lead_info.get("full_name"),
#   #   "email_id": wb_lead_info.get("email"),
#   #   "mobile_no": formatted_phone_number
#   # }
#   # frappe.get_doc(data).insert(ignore_permissions=True)
#   frappe.logger().info("Lead data from google ads: {}".format(new_lead))
#   return {"message": "Lead created successfully", "lead_name": new_lead.name}