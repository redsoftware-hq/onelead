import frappe
import json
import requests
from frappe.utils import now
from datetime import datetime
from werkzeug.wrappers import Response
import frappe.utils
from hashlib import sha1
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


def leadgen():
    """ Process lead data from Meta Ads webhook """
    try:
        data = frappe.request.json
        frappe.logger().info(f"Received POST request body: {json.dumps(data)}")

        # Log incoming payload
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "leadgen":
                    lead_data = change.get("value")
                    leadgen_id = lead_data.get("leadgen_id")
                    page_id = lead_data.get("page_id")
                    form_id = lead_data.get("form_id")
                    ad_id = lead_data.get("ad_id")
                    created_time = lead_data.get("created_time")

                    # Create a log entry
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

                    # Check if the form is configured
                    configured_form = frappe.db.exists("Meta Lead Form", {"form_id": form_id})
                    config = get_lead_config(page_id, form_id)

                    if configured_form:
                        form_doc = frappe.get_doc("Meta Lead Form", {"form_id": form_id})
                        lead_log.set("lead_doctype", form_doc.lead_doctype_reference)

                    if config:
                       lead_log.set("config_reference", config.name)
                       lead_log.set("campaign", config.campaign)

                    if not configured_form:
                        lead_log.set("processing_status", "Unconfigured")
                        lead_log.set("error_message", "No configuration found for form_id in 'Meta Lead Form'")
                    elif not config:
                        # If configuration or form is not found, log as Unconfigured
                        lead_log.set("processing_status", "Unconfigured")
                        lead_log.set("error_message", "No configuration found for page_id and form_id in 'Meta Ads Webhook Config'")

                    lead_log.insert(ignore_permissions=True)

        return Response("Lead Logged", status=200)
    except Exception as e:
        frappe.logger().error(f"Error in Logging lead: {str(e)}", exc_info=True)
        return Response(f"Error: {str(e)}", status=500)

# def leadgen():
#   try:
#     # Log the incoming request body (POST)
#     data = frappe.request.json
#     frappe.logger().info(f"Meta webhook request log from local dict: {json.dumps(frappe.local.form_dict)}")
#     frappe.logger().info(f"Received POST request body: {json.dumps(data)}")

#     # Log the incoming request data in Meta Lead Logs
#     lead_log = frappe.new_doc("Meta Lead Logs")
#     lead_log.set('json', json.dumps(data))

#     # frappe.get_doc({
#     #   "doctype": "Meta Lead Logs",
#     #   "json": json.dumps(data)
#     # }).insert(ignore_permissions=True)

#     frappe.logger().info("Processing Facebook request body")
#     process_lead_changes(data, lead_log)
#     return Response("Lead processed", status=200)

#   except Exception as e:
#     frappe.logger().error(f"Error in processing lead: {str(e)}", exc_info=True)
#     return Response(f"Error in processing lead: {str(e)}", status=500)

# def calculate_signature(payload):
#     app_secret = frappe.conf.facebook_app_secret
#     mac = hmac.new(bytes(app_secret, 'utf-8'), msg=payload, digestmod=sha1)
#     return mac.hexdigest()

# def verify_signature(request, calculated_signature):
#     signature = calculated_signature
#     # print(signature)
#     if not signature:
#         return False

#     sha_name, signature = signature.split('=')
#     mac = hmac.new(bytes(frappe.conf.facebook_app_secret, 'utf-8'), msg=request.get_data(), digestmod=sha1)
#     return hmac.compare_digest(mac.hexdigest(), signature)
# def lead_exists(page_id, leadgen_id):
#     """ Check if a lead already exists """
#     try:
#         frappe.get_doc("Meta Lead Logs", f"{page_id}_{leadgen_id}")
#         return True
#     except frappe.DoesNotExistError:
#         return False


def get_lead_config(page_id, form_id=None):
    """ Retrieve lead configuration based on page_id (and optionally form_id) in Meta Ads Webhook Config """
    filters = {"page": page_id}
    config_name = frappe.get_all("Meta Ads Webhook Config", filters=filters, limit=1)
    
    if config_name:
        config = frappe.get_doc("Meta Ads Webhook Config", config_name[0].name)
        
        # If a form_id is provided, ensure the form exists in the config's forms list
        if form_id:
            form_exists = any(form.form_id == form_id for form in config.forms_list)
            if not form_exists:
                return None  # Return None if the form_id does not exist in config

        return config  # Return the full config document if checks pass

    return None  # No configuration found for the page_id

def convert_epoch_to_frappe_date(epoch_time):
    """Convert epoch time to Frappe's date-time format."""
    # Convert epoch time to a datetime object
    dt = datetime.fromtimestamp(epoch_time)
    # Format the datetime object to Frappe's preferred format
    frappe_date = dt.strftime('%Y-%m-%d %H:%M:%S')
    return frappe_date

# def process_lead_changes(data, lead_log):
#     """ Process entries and changes in webhook data """
#     if "entry" not in data:
#         return

#     for entry in data["entry"]:
#         if "changes" not in entry:
#             continue

#         for change in entry["changes"]:
#             if change["field"] == "leadgen":
#                 leadgen_id = change["value"].get("leadgen_id")
#                 page_id = change["value"].get("page_id")

#                 if not leadgen_id or not page_id:
#                     continue

#                 if lead_exists(page_id, leadgen_id):
#                     frappe.logger().info(f"Lead {leadgen_id} already exists!")
#                     return

#                 lead_log.set("leadgen_id", leadgen_id)
#                 lead_log.set("page_id", page_id)
                
#                 config = get_lead_config(page_id)
#                 if config:
#                     lead_log.set("meta_ads_config", config.name)
#                     lead_log.set("lead_doctype_reference", config.lead_doctype)
#                     lead_log.insert(ignore_permissions=True)
#                     fetch_lead_data(leadgen_id, config, lead_log)
#                 else:
#                     frappe.logger().error(f"No lead configuration found for page_id: {page_id}")

def process_lead_changes(data, lead_log):
  try:
    if "entry" in data:
      for entry in data["entry"]:
        if "changes" in entry:
          for change in entry["changes"]:
            if change["field"] == "leadgen":
              leadgen_id = change["value"].get("leadgen_id")              
              # adgroup_id = change["value"].get("adgroup_id")
              page_id = change["value"].get("page_id")

              try:
                lead_exists = frappe.get_doc("Meta Lead Logs", f"{page_id}_{leadgen_id}")

                if lead_exists:
                  frappe.logger().info(f"Lead with leadgen_id {leadgen_id} exists!")
                  return
              except:
                # New Lead entry, no lead found.
                pass
                
              lead_log.set("leadgen_id", leadgen_id)
              lead_log.set("page_id", page_id)
              
              lead_conf = None 

              # Only during testing there won't be any page_id. when hit from developer plateform webhook.
              if page_id:
                  filters = {}
                  # if adgroup_id:
                  #     filters['ad_group_id'] = adgroup_id
                  if page_id:
                      filters['page_id'] = page_id
              
              lead_conf = frappe.get_all('Meta Ad Campaign Config', filters=filters, limit_page_length=1)

              if lead_conf and len(lead_conf) > 0 and leadgen_id:

                # Call and fetch doc data again, to fetch all child table data as well.
                config = frappe.get_doc('Meta Ad Campaign Config', lead_conf[0]['name'])
                lead_log.set("meta_ads_config", config.name)
                lead_log.set("lead_doctype_reference", config.lead_doctype)

                lead_log.insert(ignore_permissions=True)

                frappe.logger().info(f"Lead configuration found for unique key: { page_id}")
                fetch_lead_data(leadgen_id, config, lead_log)
              else:
                frappe.logger().error(f"No lead configuration found for unique key: { page_id}")

  except Exception as e:
    frappe.logger().error(f"Error in processing lead changes: {str(e)}", exc_info=True)
    raise

def fetch_lead_data(leadgen_id, lead_conf, lead_log):
  try:
    conf = frappe.get_doc("Meta Webhook Config")
    url = f"{conf.meta_url}/{conf.meta_api_version}/{leadgen_id}/"

    user_access_token = get_decrypted_password('Meta Ad Campaign Config', lead_conf.name, 'user_access_token')
    # access_token = get_decrypted_password("Meta Webhook Config", conf.name, "access_token")
    params = {"access_token": user_access_token}
    frappe.logger().info(f"Fetching lead data from Meta API for leadgen_id: {leadgen_id}")
    response = requests.get(url, params=params)

    if response.status_code == 200:
      frappe.logger().info(f"Successfully fetched lead data for leadgen_id: {leadgen_id}")
      lead_data = response.json()
      lead_log.set("lead_json", lead_data)
      lead_log.save(ignore_permissions=True)

      new_lead = process_lead_data(lead_data, lead_conf)
      print(new_lead)
      # lead_log.set("lead_doctype", new_lead.get("lead_name"))
      lead_log.set("lead_entry_successful", True)
      lead_log.save(ignore_permissions=True)

      return new_lead
    else:
      frappe.logger().error(f"Failed to fetch lead data for leadgen_id: {leadgen_id}. Status Code: {response.status_code}, Response: {response.text}")
  
  except requests.RequestException as e:
    lead_log.set("error", f"Request error while fetching lead data: {str(e)}")
    lead_log.save(ignore_permissions=True)
    frappe.logger().error(f"Request error while fetching lead data: {str(e)}", exc_info=True)
    raise
  
  except Exception as e:
    lead_log.set("error", f"Error in fetching lead data: {str(e)}")
    lead_log.save(ignore_permissions=True)
    frappe.logger().error(f"Error in fetching lead data: {str(e)}", exc_info=True)
    raise

def process_lead_data(lead_data, lead_conf):
  try:
    field_data = lead_data.get("field_data", [])
    lead_doctype = lead_conf.get('lead_doctype')
    new_lead = frappe.new_doc(lead_doctype)
    wb_lead_info = {field["name"]: field["values"][0] for field in field_data}

    frappe.logger().info(f"Processing lead data: {wb_lead_info}")
    
    for mapping in lead_conf.mapping:
      ad_form_key = mapping.ad_form_field_key
      lead_doc_field = mapping.lead_doctype_field

      if ad_form_key in wb_lead_info:
        ad_form_value = wb_lead_info.get(ad_form_key)
        if ad_form_key == "phone_number":
          ad_form_value = formate_phone_number(wb_lead_info.get(ad_form_key))
        new_lead.set(lead_doc_field, ad_form_value)

    for constant in lead_conf.constants:
      new_lead.set(constant.lead_doctype_field, constant.constant_value)

    # if lead_conf.time_field:
    #   new_lead.set(lead_conf.lead_doctype_time_field, format_epoch_time())

    new_lead.insert(ignore_permissions=True)
    frappe.db.commit()

    frappe.logger().info(f"Lead created successfully with name: {new_lead.name}")
    return {"message": "Lead created successfully", "lead_name": new_lead.name}
  
  except Exception as e:
    frappe.logger().error(f"Error in processing lead data: {str(e)}", exc_info=True)
    raise


def formate_phone_number(phone_number):
    if phone_number and phone_number.startswith("+"):
        phone_number = phone_number.replace(" ", "").replace("-", "")
        return f"{phone_number[:3]}-{phone_number[3:]}"
    else:
        return phone_number

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