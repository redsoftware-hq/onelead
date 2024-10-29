import frappe
from datetime import datetime
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.user import User
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.leadgenform import LeadgenForm

@frappe.whitelist()
def get_adaccounts():
    
    # check for user login
    if not frappe.session.user or frappe.session.user == 'Guest':
      frappe.throw("You must be logged in to access this function.")
    
    # check for user access
    if not frappe.has_permission(doctype="Meta Webhook Config", ptype="read"):
        frappe.throw("You do not have permission to access Meta Webhook Config.")
    
    meta_config = frappe.get_single("Meta Webhook Config")
    app_id = meta_config.app_id
    app_secret = meta_config.get_password("app_secret")  # Automatically decrypts
    user_token = meta_config.get_password("user_access_token")  

    # Check if all fields has data.
    if not app_id or not app_secret or not user_token:
        frappe.throw("App ID, App Secret, and User Token must all be provided in Meta Webhook Config.")
    

    FacebookAdsApi.init(app_id, app_secret, user_token)
    
    try:
        # Get the user object
        user = User(fbid='me')
        
        # Fetch Ad Accounts
        ad_accounts = user.get_ad_accounts(fields=[
            'id', 
            'account_id', 
            'name', 
            'business_name', 
            'account_status', 
            'currency', 
            'promote_pages{id,name}', 
            'business_country_code', 
            'business_city', 
            'business_state', 
            'business_zip'
        ])
        
        for ad_account in ad_accounts:
            # Check if the account has associated pages

            pages = ad_account.get('promote_pages', {}).get("data", [])

            print(pages)
            if len(pages) == 0:
                # Skip this ad account if there are no pages
                continue
            
            # Extract details from the ad account
            account_id = ad_account['account_id']
            id = ad_account['id']
            account_name = ad_account.get('name', 'No Name')
            account_status = ad_account.get('account_status')
            business_name = ad_account.get('business_name', 'No Business Name')
            business_country_code = ad_account.get('business_country_code', '')
            business_city = ad_account.get('business_city', '')
            business_state = ad_account.get('business_state', '')
            business_zip = ad_account.get('business_zip', '')
            currency = ad_account.get('currency', '')
            
            # Create or update the Ad Account in Frappe
            ad_account_doc = frappe.get_doc("Meta Ad Account", {"account_id": account_id}) if frappe.db.exists("Meta Ad Account", {"account_id": account_id}) else frappe.new_doc("Meta Ad Account")
            ad_account_doc.update({
                "account_id": account_id,
                "act_id": id,
                "account_name": account_name,
                "account_status": account_status,
                "business_name": business_name,
                "business_country_code": business_country_code,
                "business_city": business_city,
                "business_state": business_state,
                "business_zip": business_zip,
                "currency": currency
            })

            # Fetch Pages for each Ad Account
            ad_account_instance = AdAccount(id)
            pages = ad_account_instance.get_promote_pages(fields=['id', 'name'])

            print(pages)
            # Add associated pages to child table in Ad Account Config
            for page in pages:
                page_id = page["id"]

                # make entry or update Meta Page DocType
                page_doc = frappe.get_doc("Meta Page", {"page_id": page_id}) if frappe.db.exists("Meta Page", {"page_id": page_id}) else frappe.new_doc("Meta Page")
                page_doc.update({
                    "page_name": page.get("name", "No Name Found"),
                    "page_id": page_id
                })
                page_doc.save(ignore_permissions=True)

            # Save the Ad Account
            ad_account_doc.save(ignore_permissions=True)
        
        frappe.db.commit()
        return "Success"

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Meta API Error")
        frappe.throw(f"Failed to connect to Meta API: {str(e)}")


@frappe.whitelist()
def fetch_campaigns(page_id, ad_account_id):
    # check for user login
    if not frappe.session.user or frappe.session.user == 'Guest':
      frappe.throw("You must be logged in to access this function.")
    
    # check for user access
    if not frappe.has_permission(doctype="Meta Webhook Config", ptype="read"):
        frappe.throw("You do not have permission to access Meta Webhook Config.")
    
    # Get the user token and app credentials from Meta Webhook Config
    meta_config = frappe.get_single("Meta Webhook Config")
    app_id = meta_config.app_id
    app_secret = meta_config.get_password("app_secret")
    user_token = meta_config.get_password("user_access_token")

    # Check if all fields has data.
    if not app_id or not app_secret or not user_token:
        frappe.throw("App ID, App Secret, and User Token must all be provided in Meta Webhook Config.")
    
    # Initialize the Facebook API
    FacebookAdsApi.init(app_id, app_secret, user_token)
    
    try:
        # Fetch campaigns associated with the given ad account
        ad_account = AdAccount(f'act_{ad_account_id}')
        campaigns = ad_account.get_campaigns(fields=[
            'id', 'name', 'objective', 'status', 'start_time', 'stop_time', 'created_time', 'ads.limit(100){id,name,status,creative{object_story_spec}}'
        ],  params={'limit': 100, 'status': ['ACTIVE']})
        
        # Loop through each campaign and save it in Meta Campaign DocType
        for campaign in campaigns:
            campaign_id = campaign['id']
            campaign_name = campaign.get('name', 'No Name')
            campaign_objective = campaign.get('objective')
            campaign_status = campaign.get('status')
            start_time = campaign.get('start_time', None)
            stop_time = campaign.get('stop_time', None)

            doc_dict = {
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "campaign_objective": campaign_objective,
                "ad_account": ad_account_id,
                "status": campaign_status,
            }

            if start_time:
                doc_dict["start_time"] = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S%z").date()
            if stop_time:
                doc_dict["stop_time"] = datetime.strptime(stop_time, "%Y-%m-%dT%H:%M:%S%z").date()

            # Create or update Meta Campaign document
            campaign_doc = frappe.get_doc("Meta Campaign", {"campaign_id": campaign_id}) if frappe.db.exists("Meta Campaign", {"campaign_id": campaign_id}) else frappe.new_doc("Meta Campaign")
            campaign_doc.update(doc_dict)
            campaign_doc.save(ignore_permissions=True)

            print(campaign)
            # Process ads associated with this campaign
            ads = campaign.get("ads", [])
            for ad in ads:
                ad_id = ad["id"]
                ad_name = ad.get("name", "No Name")
                ad_status = ad.get("status")
                
                # Check if the ad has a lead generation form in its creative
                has_lead_form = False
                if ad.get("creative") and ad["creative"].get("object_story_spec") and ad["creative"]["object_story_spec"].get("call_to_action"):
                    call_to_action = ad["creative"]["object_story_spec"]["call_to_action"]
                    has_lead_form = "lead_gen_form_id" in call_to_action.get("value", {})

                # Prepare ad doc dictionary
                ad_doc_dict = {
                    "ads_id": ad_id,
                    "ads_name": ad_name,
                    "status": ad_status,
                    "campaign": campaign_id,
                    "has_form": has_lead_form
                }

                # Upsert Meta Ads document
                ad_doc = frappe.get_doc("Meta Ads", {"ads_id": ad_id}) if frappe.db.exists("Meta Ads", {"ads_id": ad_id}) else frappe.new_doc("Meta Ads")
                ad_doc.update(ad_doc_dict)
                ad_doc.save(ignore_permissions=True)
        
        frappe.db.commit()
        return "Success"

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Meta API Error")
        frappe.throw(f"Failed to fetch campaigns: {str(e)}")



@frappe.whitelist()
def fetch_forms_based_on_selection(campaign_id, ad_account_id, page_id, ad_id=None):
    # check for user login
    if not frappe.session.user or frappe.session.user == 'Guest':
      frappe.throw("You must be logged in to access this function.")
    
    # check for user access
    if not frappe.has_permission(doctype="Meta Webhook Config", ptype="read"):
        frappe.throw("You do not have permission to access Meta Webhook Config.")
    
    # Get credentials from Meta Webhook Config
    meta_config = frappe.get_single("Meta Webhook Config")
    app_id = meta_config.app_id
    app_secret = meta_config.get_password("app_secret")
    user_token = meta_config.get_password("user_access_token")
    
    if not app_id or not app_secret or not user_token:
        frappe.throw("App ID, App Secret, and User Token must all be provided in Meta Webhook Config.")
    
    # Initialize the Facebook API
    FacebookAdsApi.init(app_id, app_secret, user_token)
    
    try:
        if ad_id:
            # Fetch forms based on the specific ad
            ad = Ad(ad_id)
            ad_data = ad.api_get(fields=['id', 'name', 'adcreatives.limit(10){object_story_spec}'])
            forms = extract_forms_from_ad(ad_data)
        else:
            # Fetch forms based on the campaign
            campaign = Campaign(campaign_id)
            ads_data = campaign.get_ads(fields=['id', 'name', 'adcreatives{object_story_spec}'], params={"limit": 100})
            forms = []
            for ad_data in ads_data:
                forms.extend(extract_forms_from_ad(ad_data))

        # Store forms in Meta Lead Form and Form List table
        for form in forms:
            # Create or update Meta Lead Form DocType
            if not frappe.db.exists("Meta Lead Form", {"form_id": form["id"]}):
                form_doc = frappe.get_doc({
                    "doctype": "Meta Lead Form",
                    "form_id": form["id"],
                    # "ads": form["ads_id"]  #commented out, as there needs to be hook for checking Ads Link present before insert
                    "campaign": campaign_id
                })
                form_doc.insert(ignore_permissions=True)

        print(forms)
        frappe.db.commit()
        return {
            "message": "Forms fetched successfully",
            "data": forms
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Meta API Error")
        frappe.throw(f"Failed to fetch forms: {str(e)}")

def extract_forms_from_ad(ad_data):
    """Extract forms from the ad creatives in the ad data."""
    forms = []
    creatives = ad_data.get("adcreatives", {}).get("data", [])
    for creative in creatives:
        object_story_spec = creative.get("object_story_spec", {})
        call_to_action = object_story_spec.get("call_to_action", {})
        form_id = call_to_action.get("value", {}).get("lead_gen_form_id")
        if form_id:
            forms.append({
                "id": form_id,
                "ads_id": ad_data["id"],
                "name": call_to_action.get("type", "no type")
            })
    return forms

@frappe.whitelist()
def fetch_form_details(doc):
    # Check if Form ID and Campaign are provided
    if not doc.form_id or not doc.campaign_id:
        frappe.throw("Both Form ID and Campaign ID are required to fetch form details.")
    
    # Get Meta Webhook Config settings for credentials
    meta_config = frappe.get_single("Meta Webhook Config")
    app_id = meta_config.app_id
    app_secret = meta_config.get_password("app_secret")
    user_token = meta_config.get_password("user_access_token")

    # Check for missing credentials
    if not app_id or not app_secret or not user_token:
        frappe.throw("Meta API credentials are missing in Meta Webhook Config.")
    
    # Initialize the Facebook API
    FacebookAdsApi.init(app_id, app_secret, user_token)
    
    try:
        # Fetch form details using the Facebook API
        lead_form = LeadgenForm(doc.form_id)
        form_data = lead_form.api_get(fields=[
            'id', 'name', 'status', 'locale', 'questions'
        ])
        
        # Populate form details in the Meta Lead Form document
        doc.form_name = form_data.get("name", "Unknown")
        doc.status = form_data.get("status", "INACTIVE")
        doc.locale = form_data.get("locale", "en_US")


        # Add questions to the child table
        questions = form_data.get("questions", [])
        for question in questions:
            doc.append("mapping", {
                "meta_field": question.get("key", ''),
                "lead_doctype_field": "", 
                "default_value": "",      
                "formatting_function": ""
            })

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Meta API Error")
        frappe.throw(f"Failed to fetch form details: {str(e)}")
