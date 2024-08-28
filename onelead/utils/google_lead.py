

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
  frappe.logger().info("Google Lead request body: {}".format(json.dumps(data)))

  if validate_request(data):
    get_lead_data(data.get("user_column_data"))
    return
  else:
    raise "issue with leads call"
  return Response(status=400, content_type="Not a valid request for google leads webhook")


def validate_request(data):
  GOOGLE_LEAD_KEY = "webhook_secret_key"
  if data.get("Google_key") == GOOGLE_LEAD_KEY:
    return True
  frappe.logger().warning("Reqeust received with Incorrect Google Webhook Key")
  return False

def get_lead_data(data):
  lead_doc = {}
  for field in data:
    lead_doc[f'{field.get("column_id")}'] = f'{field.get("string_value")}'

  print(lead_doc)
  frappe.logger().info("Lead data from google ads: {}", lead_doc)
  return

  # $ curl -v -X POST --header "Content-Type:application/json" -d @google_lead.txt http://oneinbox.localhost:8000/api/method/onelead.utils.google_lead.webhook
