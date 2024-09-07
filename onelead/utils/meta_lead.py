"""Webhook."""
import frappe
import json
import requests
import time
from werkzeug.wrappers import Response
import frappe.utils

@frappe.whitelist(allow_guest=True)
def webhook():
  """ Meta Ads Webhook """
  if frappe.request.method == "GET":
    return validate()
  return leadgen()


def validate():
	"""Validate connection by webhook token verification"""
	hub_challenge = frappe.form_dict.get("hub.challenge")
	webhook_verify_token = frappe.db.get_single_value(
		"Meta Webhook Config", "webhook_verify_token"
	)
	if frappe.form_dict.get("hub.verify_token") != webhook_verify_token:
		frappe.throw("Verify token does not match")

	return Response(hub_challenge, status=200)

def leadgen():
  # data = frappe.local.form_dict
  data = frappe.request.json
  frappe.get_doc({
    "doctype": "Meta Lead Logs",
    "json": json.dumps(data)
  }).insert(ignore_permissions=True)
  frappe.logger().info("Facebook request body: {}".format(json.dumps(data)))
  process_lead_changes(data)
  return

def process_lead_changes(data):
  if "entry" in data:
    for entry in data["entry"]:
      if "changes" in entry:
        for change in entry["changes"]:
          if change["field"] == "leadgen":
            leadgen_id = change["value"]["leadgen_id"]
            ad_id = change["value"]["ad_id"]
            lead_conf = frappe.get_all('Meta Ad Campaign Config', filters={'ad_group_id': change["value"]["adgroup_id"]}, limit_page_length=1)
            # adgroup_id, created_time, - Single form can be used in multiple add, so use adgroup Id as ref. 
            fetch_lead_data(leadgen_id, lead_conf)


def fetch_lead_data(leadgen_id, lead_conf):
  conf = frappe.get_doc("Meta Webhook Config")

  print("FETCH LEAD DATA....")
  url = f"{conf.meta_url}/{conf.meta_api_version}/{leadgen_id}"
  params = {"access_token": conf.access_token}
  response = requests.get(url, params=params)
  print("RESPONSE", response)
  if response.status_code == 200:
    lead_data = response.json()
    process_lead_data(lead_data, lead_conf)


def process_lead_data(lead_data, lead_conf):
  field_data = lead_data.get("field_data", [])
  new_lead = frappe.new_doc(lead_conf.get('lead_doctype'))
  wb_lead_info = {field["name"]: field["values"][0] for field in field_data}
  print(wb_lead_info)
  
  for mapping in lead_conf.mapping:
    ad_form_key = mapping.ad_form_field_key
    lead_doc_field = mapping.lead_doctype_field

    if ad_form_key in wb_lead_info:
      new_lead.set(lead_doc_field, wb_lead_info.get(ad_form_key))

    for constant in lead_conf.constants:
      new_lead.set(constant.lead_doctype_field, constant.constant_value)

  new_lead.insert(ignore_permissions=True)
  frappe.db.commit()
  # # Format phone number if it contains a country code
  # phone_number = wb_lead_info.get("phone_number")
  # if phone_number and phone_number.startswith("+"):
  #   phone_number = phone_number.replace(" ", "").replace("-", "")
  #   formatted_phone_number = f"{phone_number[:3]}-{phone_number[3:]}"
  # else:
  #   formatted_phone_number = phone_number

  # data = {
  #   "doctype": "Leads",
  #   "lead_name": wb_lead_info.get("full_name"),
  #   "email_id": wb_lead_info.get("email"),
  #   "mobile_no": formatted_phone_number
  # }
  # frappe.get_doc(data).insert(ignore_permissions=True)
  frappe.logger().info("Lead data from google ads: {}".format(new_lead))
  return {"message": "Lead created successfully", "lead_name": new_lead.name}