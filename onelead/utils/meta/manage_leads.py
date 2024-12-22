import frappe
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.lead import Lead
from . import formatting_functions
# from your_meta_sdk_module import MetaAdsAPI 

def process_logged_lead(doc, method):
  """Process a lead after it's logged in Meta Webhook Lead Logs."""
  try:
      # Retrieve the form configuration for the given form_id
      form_config = frappe.get_doc("Meta Lead Form", {"form_id": doc.form_id})

      # If form configuration is not found, update log status and exit - already configured. just setting up error.
      if not form_config:
          doc.db_set("processing_status", "Unconfigured")
          doc.db_set("error_message", f"No configuration found for form_id: {doc.form_id}")
          return
      
      meta_config = frappe.get_single("Meta Webhook Config")
      if meta_config.page_flow:
        if doc.config_not_enabled:
          doc.db_set("processing_status", "Disabled")
          doc.db_set("error_message", "Configuration {doc.config_reference} is not Enabled")
          return
        if form_config.campaign:
            doc.db_set("campaign", form_config.campaign)
        else:
            try:
                ads_doc = frappe.get_doc("Meta Ads", doc.ad_id)
                form_config.db_set("campaign", ads_doc.campaign)
                doc.db_set("campaign", ads_doc.campaign)
            except Exception as e:
                frappe.logger().error(f"Error in setting campaign for leadgen_id {doc.leadgen_id}")
                frappe.db_set("error_message", f"Error in setting campaign for leadgen_id {doc.leadgen_id}")


      # Use Meta SDK to fetch lead data
      lead_data = fetch_lead_from_meta(doc.leadgen_id, meta_config)

      if lead_data:
          # Map and create lead Entry
          lead_doc = create_lead_entry(lead_data, form_config, doc)
          doc.db_set("processing_status", "Processed")
          doc.db_set("lead_doc_reference", lead_doc.name)
      else:
          doc.db_set("processing_status", "Error")
          doc.db_set("error_message", "Failed to retrieve lead details from Meta API")

  except Exception as e:
      doc.db_set("processing_status", "Error")
      doc.db_set("error_message", str(e))
      frappe.logger().error(f"Error in processing lead for leadgen_id {doc.leadgen_id}: {str(e)}", exc_info=True)
    


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

        lead = Lead(leadgen_id).api_get()
        
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
        
        # Retrieve the field value from ads_config_doc
        if hasattr(form_doc, default_field_name):
            field_value = getattr(form_doc, default_field_name)
            return field_value
        elif hasattr(ads_config_doc, default_field_name):
            field_value = getattr(ads_config_doc, default_field_name)
            return field_value
        else:
            frappe.logger().warning(f"Field {default_field_name} not found in {log_doc.config_doctype_name} and Meta Lead Form")
            return default_value

def create_lead_entry(lead_data, form_doc, log_doc):
    """Create a new Lead record in Frappe based on Meta lead data and form configuration."""
    try:
        field_data = lead_data.get("field_data", [])
        meta_lead_info = {field["name"]: field["values"][0] for field in field_data}
        
        new_lead = frappe.new_doc(form_doc.lead_doctype_reference)

        # Map the fields according to form configuration
        for mapping in form_doc.mapping:
            meta_field = mapping.meta_field
            lead_field = mapping.lead_doctype_field
            default_value = mapping.default_value
                
            # Use the default value if no data is provided from Meta
            field_value = meta_lead_info.get(meta_field, process_default_value(default_value, log_doc, form_doc))

            # If a custom formatting function is specified, apply it
            if mapping.formatting_function:
                try:
                    # Split by comma to get function name and arguments
                    func_name, *args = [arg.strip() for arg in mapping.formatting_function.split(',')]
                    formatting_func = getattr(formatting_functions, func_name, None)
                    
                    # Call the function with field_value and additional arguments
                    if formatting_func:
                        field_value = formatting_func(field_value, *args)
                except Exception as e:
                    frappe.logger().error(f"Error in formatting function '{mapping.formatting_function}' for {lead_field}: {str(e)}")


            new_lead.set(lead_field, field_value)

        # Insert the new lead and commit to database
        new_lead.insert(ignore_permissions=True)
        frappe.db.commit()
        
        frappe.logger().info(f"Lead created successfully with name: {new_lead.name}")
        return new_lead

    except Exception as e:
        frappe.logger().error(f"Error creating lead document: {str(e)}", exc_info=True)
        raise
    

# Example setup for calling the function dynamically
def call_function_dynamically(func, value, *args):
    # Check the function's parameter count
    func_param_count = func.__code__.co_argcount

    # Call with only the required number of arguments
    if func_param_count == 1:
        # Function only expects one argument (e.g., value)
        return func(value)
    elif func_param_count == 2:
        # Function expects two arguments (e.g., value, code)
        return func(value, args[0] if args else None)
    else:
        # Function expects more than two arguments
        return func(value, *args[:func_param_count - 1])