

import frappe
import json
import requests
import time
from werkzeug.wrappers import Response
import frappe.utils

@frappe.whitelist(allow_guest=True)
def webhook():
  """ Google Ads Form Webhook """
  if frappe.request.method == "POST":
    handle_lead()
  return

def handle_lead():
  # data = frappe.local.form_dict
  data = frappe.request.json
  frappe.get_doc({
    "doctype": "Google Lead Logs",
    "json": json.dumps(data)
  }).insert(ignore_permissions=True)
  frappe.logger().info("Google Lead request body: {}".format(json.dumps(data)))

  config = validate_request(data)
  if config is not False:
    try:
      get_lead_data(data.get("user_column_data"), config)
    except Exception as e:
      frappe.logger().error(f"Google Lead Webhook request: unexpected error. {e}")
      return Response("Something went wrong in webhook", status=500, content_type="text/plain")
    return
  # else:
    # raise Exception("Issue with leads call")
  return Response("Error occured in google leads webhook", status=400, content_type="text/plain")

def validate_request(data):
  # TODO: Check if it's possible to add meta config read only fields to meta ad config.
  config = frappe.get_all('Google Ad Campaign Config', filters={'campaign_id': data.get("campaign_id")}, limit_page_length=1)
  if not config or len(config) == 0:
    frappe.logger().error(f"Google Lead webhook request: NO CONFIG DEFINED FOR campaign_ID {data.get('campaign_id')}")
    return False
  
  config = frappe.get_doc('Google Ad Campaign Config', config[0]['name'])

  GOOGLE_LEAD_KEY = config.get('webhook_key')
  if data.get("google_key") != GOOGLE_LEAD_KEY:
    frappe.logger().error("Google Lead webhook request: WEBHOOK KEY DOES NOT MATCH !")
    return False
  return config

def get_lead_data(data, lead_config):
  lead = frappe.new_doc(lead_config.get('lead_doctype'))
  # webhook_form_fields = [field['column_id'] for field in data]
  webhook_form_dict = {field.get('column_id'): field.get('string_value') for field in data}

  # Fetch Mapping fields
  for mapping in lead_config.mapping:
    ad_form_key = mapping.ad_form_field_key
    lead_doc_field = mapping.lead_doctype_field

    # Set all values from Ad form to Lead doctype
    if ad_form_key in webhook_form_dict:
      ad_form_value = webhook_form_dict.get(ad_form_key)
      if ad_form_key == "PHONE_NUMBER":
        ad_form_value = formate_phone_number(ad_form_value)

      lead.set(lead_doc_field, ad_form_value)

    # Set Constant Values for lead doctype.
    for constant in lead_config.constants:
      lead.set(constant.lead_doctype_field, constant.constant_value)


  lead.insert(ignore_permissions=True)
  frappe.db.commit()
  # lead_doc = {}
  # for field in data:
  #   lead_doc[f'{field.get("column_id")}'] = f'{field.get("string_value")}'

  frappe.logger().info("Lead data from google ads: {}".format(lead))
  return {"message": "Lead created successfully", "lead_name": lead.name}

  # $ curl -v -X POST --header "Content-Type:application/json" -d @google_lead.txt http://oneinbox.localhost:8000/api/method/onelead.utils.google_lead.webhook

def formate_phone_number(phone_number):
    if phone_number and phone_number.startswith("+"):
        phone_number = phone_number.replace(" ", "").replace("-", "")
        return f"{phone_number[:3]}-{phone_number[3:]}"
    else:
        return phone_number