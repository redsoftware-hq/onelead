"""Webhook."""
import frappe
import json
import requests
import time
from werkzeug.wrappers import Response
import frappe.utils


def webhook():
  """ Meta Ads Webhook """
  if frappe.request.method == "GET":
    return validate()
  return leadgen()


def validate():
	"""Validate connection by webhook token verification"""
	hub_challenge = frappe.form_dict.get("hub.challenge")
	# webhook_verify_token = frappe.db.get_single_value(
	# 	"Messenger Config", "webhook_verify_token"
	# )

	if frappe.form_dict.get("hub.verify_token") != "webhook_verify_token":
		frappe.throw("Verify token does not match")

	return Response(hub_challenge, status=200)

def leadgen():
  data = frappe.local.form_dict
  frappe.logger().info("Facebook request body: {}".format(json.dumps(data)))
  # frappe.get_doc({
  #   "doctype": "Webhook Logs FB",
  #   "json_data": json.dumps(data)
  # }).insert(ignore_permissions=True)

def process_lead_changes(data):
    if "entry" in data:
        for entry in data["entry"]:
            if "changes" in entry:
                for change in entry["changes"]:
                    if change["field"] == "leadgen":
                        leadgen_id = change["value"]["leadgen_id"]
                        fetch_lead_data(leadgen_id)


def fetch_lead_data(leadgen_id):
    conf = frappe.get_conf()
    print("FETCH LEAD DATA....")
    url = f"https://graph.facebook.com/v11.0/{leadgen_id}"
    params = {"access_token": conf.access_token}
    response = requests.get(url, params=params)
    print("RESPONSE", response)
    if response.status_code == 200:
        lead_data = response.json()
        process_lead_data(lead_data , conf.api_key, conf.api_secret)


def process_lead_data(lead_data, api_key, api_secret):
    field_data = lead_data.get("field_data", [])
    lead_info = {field["name"]: field["values"][0] for field in field_data}
    print(lead_info)
    
    # Format phone number if it contains a country code
    phone_number = lead_info.get("phone_number")
    if phone_number and phone_number.startswith("+"):
        phone_number = phone_number.replace(" ", "").replace("-", "")
        formatted_phone_number = f"{phone_number[:3]}-{phone_number[3:]}"
    else:
        formatted_phone_number = phone_number

    data = {
        "doctype": "Leads",
        "lead_name": lead_info.get("full_name"),
        "email_id": lead_info.get("email"),
        "mobile_no": formatted_phone_number
    }
    frappe.get_doc(data).insert(ignore_permissions=True)
    return