import frappe
import json
from datetime import datetime
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.lead import Lead
# from .. import formatting_functions
from ..formatting_functions import FORMATTING_FUNCTIONS
from ..meta_lead import get_lead_config
# from your_meta_sdk_module import MetaAdsAPI 


# ================== Utility Functions ==================

def ensure_campaign_exists(form_doc):
    """Ensure a campaign exists for the given Meta Lead Form."""
    try:
        # Generate campaign ID based on form name and form ID
        campaign_id = f"{form_doc.form_name.replace(' ', '_')}_{form_doc.form_id}"
        campaign_name = form_doc.form_name or f"Campaign for {form_doc.form_id}"
        campaign_objective = "OUTCOME_LEADS"

        # Check if a campaign with the generated ID already exists
        existing_campaign = frappe.db.exists("Meta Campaign", {"campaign_id": campaign_id})

        if existing_campaign:
            return existing_campaign  # Return the existing campaign ID
        
        # Create a new campaign document
        new_campaign = frappe.get_doc({
            "doctype": "Meta Campaign",
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "campaign_objective": campaign_objective,
            "status": "ACTIVE",
            "has_lead_form": 1,
            "self_created": 1,
            "assignee_doctype": form_doc.assignee_doctype,
            "assign_to": form_doc.assign_to
        })
        
        new_campaign.insert(ignore_permissions=True)
        frappe.db.commit()

        return new_campaign.name  # Return new campaign ID

    except Exception as e:
        frappe.logger().error(f"Error ensuring campaign exists for form_id {form_doc.form_id}: {str(e)}")
        return None

def ensure_ads_exists(form_doc, doc, ads_id=None):
    """Ensure an ads exists for the given Meta Lead Form."""
    try:
        current_date = datetime.now().strftime("%d%m%Y")
        # Generate Ads ID and Name
        ads_id = ads_id or f"{form_doc.form_name.replace(' ', '_')}_{form_doc.form_id}"
        ads_name = f"{form_doc.form_name.replace(' ', '_').replace('-', '_')}_{current_date}" if form_doc.form_name else f"Ads_for_{form_doc.form_id}_{current_date}"

        # Check if an Ads with this ID exists
        existing_ads = frappe.db.exists("Meta Ads", {"ads_id": ads_id})

        if existing_ads:
            existing_ads_doc = frappe.get_doc("Meta Ads", existing_ads)
            # if existing_ads_doc.campaign:
            #     # TODO: 1a. remove this under form M:M campaign deps.
            #     form_doc.db_set("campaign", existing_ads_doc.campaign)
            #     # 1a.remove form_doc.campaign condition. 
            # elif form_doc.campaign and not existing_ads_doc.campaign:
            #     existing_ads_doc.db_set("campaign", form_doc.campaign)
            # elif not existing_ads_doc.campaign and not form_doc.campaign:
            if not existing_ads_doc.campaign:
                campaign_id = ensure_campaign_exists(form_doc)
                if not campaign_id:
                    frappe.throw(f"Could not create or find a campaign for form_id: {form_doc.form_id}")
                # 1a. remove form_doc.camapgin under form M:M campaign deps.
                # form_doc.db_set("campaign", campaign_id)
                doc.db_set("campaign", campaign_id)
                existing_ads_doc.db_set("campaign", campaign_id)
            return existing_ads  # Return the existing Ads ID

        # If the campaign is missing, create it first
        # TODO: 1a. remove form_doc.campaign condition, directly make sure that campaign exists and assign it to ads.
        # if not form_doc.campaign:
        campaign_id = ensure_campaign_exists(form_doc)
        doc.db_set("campaign", campaign_id)
        # if campaign_id:
        #     form_doc.db_set("campaign", campaign_id)
        # else:
        if not campaign_id:
            frappe.throw(f"Could not create or find a campaign for form_id: {form_doc.form_id}")

        # Create a new Meta Ads document
        new_ads = frappe.get_doc({
            "doctype": "Meta Ads",
            "ads_id": ads_id,
            "ads_name": ads_name,
            "status": form_doc.status if form_doc.status else "PAUSED",
            # "campaign": form_doc.campaign or campaign_id,
            "campaign": campaign_id,
            "has_lead_form": 1
        })

        new_ads.insert(ignore_permissions=True)
        frappe.db.commit()

        return new_ads.name  # Return new Ads ID

    except Exception as e:
        frappe.logger().error(f"Error ensuring Ads exists for form_id {form_doc.form_id}: {str(e)}")
        return None


@frappe.whitelist()
def bulk_manual_retry_lead_processing(docnames):
    """
    Enqueue a background job to process multiple lead logs in bulk.
    """
    if isinstance(docnames, str):
        docnames = json.loads(docnames)

    # Enqueue the worker job
    frappe.enqueue(
        "onelead.utils.meta.manage_leads._process_lead_logs_in_bulk",
        docnames=docnames,
        queue='long'
    )
    return {"status": "queued"}

def _process_lead_logs_in_bulk(docnames):
    """
    Actual worker function that processes each docname in the background.
    """
    for docname in docnames:
        try:
            doc = frappe.get_doc("Meta Webhook Lead Logs", docname)
            # Re-run your manual retry function or call the logic directly
            manual_retry_lead_processing(docname)
        except Exception as e:
            frappe.logger().error(f"Bulk job error for doc {docname}: {str(e)}", exc_info=True)

@frappe.whitelist()
def manual_retry_lead_processing(docname=None, doc=None):
    """Manually retry processing a lead log entry."""
    try:
        if doc and not isinstance(doc, frappe.model.document.Document):
            if isinstance(doc, dict):
                # Possibly convert to a Document via frappe._dict or re-fetch from DB
                doc = frappe.get_doc("Meta Webhook Lead Logs", doc.get("name"))

        if not doc and docname:
            doc = frappe.get_doc("Meta Webhook Lead Logs", docname)
        if not doc:
            frappe.throw("No valid doc or docname provided for manual retry.")

        if doc.processing_status in ["Processed", "Pending"]:
            return {"status": "success", "message": "Lead already processed or is pending."}

        # If the doc is "Unconfigured" or missing key fields (like config_reference or lead_doctype),
        # attempt to re-derive them from current Meta Webhook Config settings.
        if doc.processing_status in ["Unconfigured", "Disabled"] or not doc.config_reference or not doc.lead_doctype:
            reconfigure_lead_log(doc)

        # After reconfiguration attempt, process the lead
        return process_logged_lead(doc, "manual")
    except Exception as e:
        frappe.logger().error(f"Error in manual retry for lead log {docname}: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

def reconfigure_lead_log(doc):
    """
    Re-derive the 'config_reference', 'lead_doctype', etc. if missing.
    Similar logic to create_lead_log but applied to an existing log doc.
    """
    try:
        # Re-fetch global config (to check if page_flow is enabled, or to locate correct doctype)
        global_conf = frappe.get_single("Meta Webhook Config")

        # 1. Check if the form exists in "Meta Lead Form"
        configured_form = frappe.db.exists("Meta Lead Form", {"form_id": doc.form_id})
        
        # 2. Attempt to find the appropriate config using existing 'page_id' and 'form_id'
        config = get_lead_config(doc.page_id, doc.form_id, global_conf)

        # Decide which doctype name we expect:
        doctype_name = "Meta Ads Page Config" if global_conf.page_flow else "Meta Ads Webhook Config"
        doc.db_set("config_doctype_name", doctype_name)

        if configured_form:
            form_doc = frappe.get_doc("Meta Lead Form", {"form_id": doc.form_id})
            doc.db_set("lead_form", doc.form_id)
            # If the 'lead_doctype_reference' is defined in that Meta Lead Form
            if form_doc.lead_doctype_reference:
                doc.db_set("lead_doctype", form_doc.lead_doctype_reference)
            else:
                doc.db_set({
                    "processing_status": "Unconfigured",
                    "error_message": f"No lead_doctype_reference found in 'Meta Lead Form' for form_id: {doc.form_id}"
                })
        else:
            doc.db_set({
                "processing_status": "Unconfigured",
                "error_message": f"No form found in `Meta Lead Form` for form_id: {doc.form_id}, please fetch forms again to get the latest forms."
            })

        # If we found a matching config doc, set config_reference, campaign, etc.
        if config:
            doc.db_set("config_reference", config.name)
            if not config.enable:
                doc.db_set("config_not_enabled", 1)
            
            # If Campaign is set Globally in the config, set it in the log doc
            if hasattr(config, "campaign") and config.campaign:
                doc.db_set("campaign", config.campaign)
        else:
            # If no config is found, mark it as Unconfigured
            doc.db_set({
                "processing_status": "Unconfigured",
                "error_message": f"No configuration found for page_id: {doc.page_id} and form_id: {doc.form_id} in '{doctype_name}'"
            })
        
        # set the doc back to "Pending" to let the process_logged_lead handle it
        # doc.db_set("processing_status", "Pending")

    except Exception as e:
        frappe.logger().error(f"Error in reconfiguring lead log {doc.name}: {str(e)}", exc_info=True)
        doc.db_set({
            "processing_status": "Error",
            "error_message": f"Error in reconfigure_lead_log: {str(e)}"
        })

def process_logged_lead(doc, method):
  """Process a lead after it's logged in Meta Webhook Lead Logs."""
  try:
      meta_config = frappe.get_single("Meta Webhook Config")

    #   FETCH LEAD DATA FROM META API
      lead_data = None
      if not doc.lead_payload:
        # Use Meta SDK to fetch lead data
        lead_data = fetch_lead_from_meta(doc.leadgen_id, meta_config)
        if lead_data:
          # Log the data first
          doc.db_set({
              "lead_payload": json.dumps(lead_data),
              "organic": lead_data.get("is_organic", False),
              "platform": 'Instagram' if lead_data.get("platform") == 'ig' else 'Facebook' if lead_data.get("platform") == 'fb' else '',
          })
      else:
        lead_data = json.loads(doc.lead_payload)

      
      # Retrieve the form configuration for the given form_id
      form_config = frappe.get_doc("Meta Lead Form", {"form_id": doc.form_id})

      # If form configuration is not found, update log status and exit - already configured. just setting up error.
      # TODO: 1b. remove this condition, as it's already handled in reconfigure_lead_log, and create_lead_log.
    #   if not form_config:
    #       doc.db_set("processing_status", "Unconfigured")
    #       doc.db_set("error_message", f"No form found in `Meta Lead Form` for form_id: {doc.form_id}, please fetch forms again to get the latest forms.")
    #       return
      if not doc.campaign and doc.ad_id:
        campaign_id = ensure_campaign_exists(form_config)
        if campaign_id:
            doc.db_set("campaign", campaign_id)

      # Ensure ads exists and update doc.ads if necessary
      if not doc.ads and doc.ad_id:
        ads_id = ensure_ads_exists(form_config, doc, doc.ad_id)
        if ads_id:
            #   1a. remove form_config.campaign for M:M relationship
            # form_config.db_set("ads", ads_id)
            doc.db_set("ads", ads_id)
    #   if not doc.camapign:
          
      
      if meta_config.page_flow:
        if doc.config_not_enabled:
          doc.db_set({
                "processing_status": "Disabled",
                "error_message": f"Configuration can be found, but {doc.config_reference} is not Enabled"
          })
          return

        # TODO: 1b. remove this condition, as it's already handled in reconfigure_lead_log, and create_lead_log.
        # Rquired last check, if form_config is not found, then exit.
        if not doc.config_reference:
            doc.db_set({
                "processing_status": "Unconfigured",
                "error_message": f"Configuration is not mapped properly, please make sure that form with form_id {doc.form_id} is mapped to a config of page {doc.page_id}"
            })
            return
        
        # This is required for adding Lead link to the log doc. so checks to make sure it exists.
        if not form_config.lead_doctype_reference:
            doc.db_set({
                "processing_status": "Unconfigured",
                "error_message": f"Lead Doctype reference is not set properly in form with form_id {doc.form_id}"
            })
            return
        if not doc.ads or not doc.campaign and doc.ad_id:
            doc.db_set({
                "processing_status": "Unconfigured",
                "error_message": "Ads and Campaign is not set in log doc"
            })
            return
        # else:
        #     try:
        #         ads_doc = frappe.get_doc("Meta Ads", doc.ad_id)
        #         form_config.db_set("campaign", ads_doc.campaign)
        #         doc.db_set("campaign", ads_doc.campaign)
        #     except Exception as e:
        #         frappe.logger().error(f"Error in setting campaign for leadgen_id {doc.leadgen_id}")
        #         doc.db_set("processing_status", "Disabled")
        #         doc.db_set("error_message", f"Error in setting campaign for leadgen_id {doc.leadgen_id}")
        #         return

      if lead_data:
          # Map and create lead Entry
          user = meta_config.lead_creator
          lead_doc = create_lead_entry(lead_data, form_config, doc, user)
          doc.db_set({
                "processing_status": "Processed",
                "lead_doc_reference": lead_doc.name,
                "error_message": ""
          })
      else:
          doc.db_set({
                "processing_status": "Error",
                "error_message": "Failed to retrieve lead details from Meta API"
          })

      if method == "manual":
          return {"status": "success", "message": "Lead processed successfully"}

  except Exception as e:
      doc.db_set({
            "processing_status": "Error",
            "error_message": str(e)
      })
      frappe.logger().error(f"Error in processing lead for leadgen_id {doc.leadgen_id}: {str(e)}", exc_info=True)
      if method == "manual":
          return {"status": "error", "message": str(e)}
    


def fetch_lead_from_meta(leadgen_id, meta_config):
    """Fetch lead details from Meta using facebook_business SDK."""
    try:
        # Initialize SDK client with access token and App
        # meta_config = frappe.get_single("Meta Webhook Config")
        app_id = meta_config.app_id
        app_secret = meta_config.get_password("app_secret")
        user_token = meta_config.get_password("user_access_token")

        # Check if all fields has data.
        if not app_id or not app_secret or not user_token:
            frappe.throw("App ID, App Secret, and User Token must all be provided in Meta Webhook Config.")
        
        # Initialize the Facebook API
        FacebookAdsApi.init(app_id, app_secret, user_token)

        lead = Lead(leadgen_id).api_get(fields=["ad_id", "campaign_id", "field_data", "form_id", "created_time", "is_organic", "platform", "post", "vehicle"])

        # convert lead to dictionary/ json
        lead = lead.export_all_data()
        
        return lead

    except Exception as e:
        frappe.logger().error(f"Error fetching lead data from Meta for leadgen_id {leadgen_id}: {str(e)}", exc_info=True)
        raise e
    
def process_default_value(default_value, log_doc, form_doc):

    # fetch ads_config doc if default_value is pased as dynamic field value. 
    ads_config_doc = frappe.get_doc(log_doc.config_doctype_name, log_doc.config_reference)

    # Check if default_value is referencing a field in the config doctype
    if isinstance(default_value, str) and default_value.startswith("field:"):
        # Extract the field name after "field:" prefix
        default_field_name = default_value.split("field:")[1].strip()
        
        # Retrieve the field value from any of the below documents
        # Priority order: log_doc → form_doc → ads_config_doc
        for source in (log_doc, form_doc, ads_config_doc):
            if hasattr(source, default_field_name):
                field_value = getattr(source, default_field_name)

                # If the field exists but is None or empty, continue checking the next source
                if field_value not in [None, ""]:
                    return field_value
    
        # If not found in any document, log a warning and return the original default_value
        frappe.logger().warning(
            f"Field '{default_field_name}' not found or is empty in {log_doc.config_doctype_name}, Meta Lead Form, and Ads Config."
        )
    return default_value

def create_lead_entry(lead_data, form_doc, log_doc, user="Administrator"):
    """Create a new Lead record in Frappe based on Meta lead data and form configuration."""
    try:
        field_data = lead_data.get("field_data", [])
        meta_lead_info = {field["name"]: field["values"][0] for field in field_data if "values" in field}
        
        new_lead = frappe.new_doc(form_doc.lead_doctype_reference)

        # Map the fields according to form configuration
        for mapping in form_doc.mapping:
            meta_field = mapping.meta_field
            lead_field = mapping.lead_doctype_field
            default_value = mapping.default_value
                
            # Use the default value if no data is provided from Meta
            field_value = meta_lead_info.get(meta_field, None)
            if not field_value:
                field_value = process_default_value(default_value, log_doc, form_doc)

            # If a custom formatting function is specified, apply it
            if mapping.formatting_function:
                try:
                    # Split by comma to get function name and arguments
                    func_name = mapping.formatting_function
                    func_params = parse_function_parameters(mapping.function_parameters)
                    # func_params = mapping.function_parameters.split(',') if mapping.function_parameters else []
                    # func_name, *args = [arg.strip() for arg in mapping.formatting_function.split(',')]
                    # formatting_func = getattr(formatting_functions, func_name, None)
                    
                    # Call the function with field_value and additional arguments
                    # if formatting_func:
                    #     field_value = formatting_func(field_value, *args)

                    if func_name in FORMATTING_FUNCTIONS:
                        formatting_func = FORMATTING_FUNCTIONS[func_name]
                        field_value = formatting_func(field_value, *func_params)
                except Exception as e:
                    frappe.logger().error(f"Error in formatting function '{mapping.formatting_function}' for {lead_field}: {str(e)}")


            new_lead.set(lead_field, field_value)

        # Insert the new lead and commit to database
        frappe.set_user(user)
        res = new_lead.insert(ignore_permissions=True)
        frappe.db.commit()
        
        frappe.logger().info(f"Lead created successfully with name: {new_lead.name}")
        return new_lead

    except Exception as e:
        frappe.logger().error(f"Error creating lead document: {str(e)}", exc_info=True)
        raise
    

def parse_function_parameters(param_string):
    if not param_string:
        return []

    param_string = param_string.strip()

    # Try JSON parsing first (for both objects & lists)
    try:
        parsed_data = json.loads(param_string)
        if isinstance(parsed_data, dict):  # JSON Object (Key-Value)
            return parsed_data
        elif isinstance(parsed_data, list):  # JSON List (Array)
            return parsed_data
    except json.JSONDecodeError:
        pass  # Not JSON, proceed with comma-separated parsing

    # Fallback: Comma-Separated String
    return [param.strip() for param in param_string.split(',') if param.strip()]


# Example setup for calling the function dynamically
# def call_function_dynamically(func, value, *args):
#     # Check the function's parameter count
#     func_param_count = func.__code__.co_argcount

#     # Call with only the required number of arguments
#     if func_param_count == 1:
#         # Function only expects one argument (e.g., value)
#         return func(value)
#     elif func_param_count == 2:
#         # Function expects two arguments (e.g., value, code)
#         return func(value, args[0] if args else None)
#     else:
#         # Function expects more than two arguments
#         return func(value, *args[:func_param_count - 1])



import frappe
from frappe.utils import now_datetime

def poll_leads():
    """Polling job to fetch leads from Meta Ads API"""
    
    config = frappe.get_single("Meta Webhook Config")
    if not config.enable_polling:
        return  # Exit if polling is disabled
    
    job_log = frappe.new_doc("Polling Summary Log")
    job_log.job_start_time = now_datetime()
    job_log.polling_interval_used = config.polling_interval

    total_leads = 0
    new_leads = 0
    duplicates = 0
    failed = 0
    error_messages = []

    try:
        # Fetch only new leads (after last polling time)
        last_poll_time = config.last_polling_time or "1970-01-01 00:00:00"
        leads = fetch_leads_from_meta(last_poll_time)
        
        total_leads = len(leads)
        
        for lead in leads:
            leadgen_id = lead.get("leadgen_id")
            
            if frappe.db.exists("Meta Webhook Lead Logs", {"leadgen_id": leadgen_id}):
                duplicates += 1
                continue  # Skip if duplicate
            
            try:
                log_entry = frappe.new_doc("Meta Webhook Lead Logs")
                log_entry.update({
                    "leadgen_id": leadgen_id,
                    "raw_payload": json.dumps(lead),
                    "received_time": now_datetime(),
                    "source": "Polling",
                    "polling_summary_reference": job_log.name
                })
                log_entry.insert(ignore_permissions=True)
                new_leads += 1
            except Exception as e:
                failed += 1
                error_messages.append(str(e))
        
        job_log.new_leads_created = new_leads
        job_log.duplicate_leads = duplicates
        job_log.failed_leads = failed
        job_log.total_leads_fetched = total_leads
        job_log.error_messages = "\n".join(error_messages)
        job_log.job_end_time = now_datetime()
        
        job_log.insert(ignore_permissions=True)
        frappe.db.commit()

        # Update last polling time
        config.db_set("last_polling_time", now_datetime())
        
    except Exception as e:
        job_log.error_messages = f"Polling failed: {str(e)}"
        job_log.insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.logger().error(f"Error in polling job: {str(e)}", exc_info=True)
