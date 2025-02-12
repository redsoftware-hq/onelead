import frappe
import requests
from datetime import datetime, timedelta
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.user import User
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.leadgenform import LeadgenForm
from facebook_business.adobjects.page import Page

from frappe.utils.background_jobs import get_job

@frappe.whitelist()
def get_latest_forms_for_page(page_id):
    try:
        refresh_token()
        forms = fetch_forms_based_on_page(page_id, {})
        form_names = [form.get("form_name") for form in forms if form.get('isNew')]
        return form_names
    except:
        frappe.throw("Failed to fetch forms for the page.")

def is_token_short_lived(doc, user_access_token, app_access_token):
    url = f"{doc.meta_url}/debug_token?input_token={user_access_token}&access_token={user_access_token}"
    response = requests.get(url)
    data = response.json()

    if not data.get('data', {}).get("is_valid"):
        frappe.throw("User access token is invalid.")
    
    token_data = data['data']
    expires_at_timestamp = token_data.get("expires_at")
    if not expires_at_timestamp:
        expires_at_timestamp = token_data.get("data_access_expires_at")

    expires_at = datetime.fromtimestamp(expires_at_timestamp) if expires_at_timestamp else None
    expires_in_days = (expires_at - datetime.now()).days if expires_at else None
    frappe_formatted_expires_at = expires_at.strftime('%Y-%m-%d %H:%M:%S') if expires_at else "N/A"

    # Check for required permissions
    required_permissions = [
        "pages_show_list",
        "ads_management",
        "ads_read",
        "leads_retrieval",
        "pages_read_engagement",
        "pages_manage_metadata",
        "pages_manage_ads",
    ]
    granted_permissions = token_data.get("scopes", [])
    missing_permissions = [perm for perm in required_permissions if perm not in granted_permissions]

    if missing_permissions:
        frappe.throw(
            title="Insufficient Permissions",
            msg=f"The user Access Token is missing the following permissions: {', '.join(missing_permissions)}, please enter correct Token with all the permissions."
        )

    is_short_lived = True if expires_in_days < 30 else False
    res = {
        "is_short_lived": is_short_lived,
        "is_valid": token_data["is_valid"],
        "user_id": token_data.get("user_id"),
    }

    return res

def get_long_lived_user_token(doc, user_access_token, app_secret, app_id):
    """Function to exchange a short-lived user token for a long-lived token."""
    try:
        url = f"{doc.meta_url}/{doc.meta_api_version}/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": user_access_token
        }
        long_token_response = requests.get(url, params=params)
        long_token_data = long_token_response.json()
        if "access_token" in long_token_data:
            # Update the token and new expiration
            long_lived_token = long_token_data["access_token"]

            expires_at_timestamp = long_token_data.get("expires_at")
            if not expires_at_timestamp:
                expires_at_timestamp = long_token_data.get("data_access_expires_at")

            expires_at = datetime.fromtimestamp(expires_at_timestamp) if expires_at_timestamp else None
            expires_in_days = (expires_at - datetime.now()).days if expires_at else None
            # expires_in_days = long_token_data.get("expires_in") / (60 * 60 * 24)  # Convert seconds to days
            frappe_formatted_expires_at = expires_at.strftime('%Y-%m-%d %H:%M:%S') if expires_at else "N/A"

            # new_expiration_date = datetime.now() + timedelta(days=expires_in_days)
            # frappe_formatted_expires_at = new_expiration_date.strftime('%Y-%m-%d %H:%M:%S')

            doc.user_access_token = long_lived_token
            doc.token_expiry = frappe_formatted_expires_at
            doc.is_token_valid = True
            doc.save(ignore_permissions=True)
            
            frappe.logger().info(f"Token exchanged successfully. Expires in {expires_in_days} days.")
            return {
                "access_token": long_lived_token,
                "expires_at": frappe_formatted_expires_at,
                "expires_in_days": expires_in_days,
                "message": "Token converted to long-lived token."
            }
        else:
            frappe.throw("Failed to generate a long-lived token.")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Token Exchange Error")
        frappe.throw(f"Failed to exchange token: {str(e)}")

def install_app_to_page(page_access_token, page_id, app_id):
    # Initialize the API with the user access token
    FacebookAdsApi.init(access_token=page_access_token)

    # Create a Page object
    page = Page(page_id)
    
    # Install the app on the Page with subscribed fields
    try:
        # Check if the app is already subscribed
        existing_subscriptions = page.get_subscribed_apps()
        for app in existing_subscriptions:
            if app.get("id") == app_id:  # Replace with your app's ID
                frappe.msgprint(f"App is already installed on page {page_id}.")
                return
        
        page.create_subscribed_app(params={"subscribed_fields": ["leadgen"]})
        frappe.msgprint(f"App successfully installed on page {page_id}.")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "App Installation Error")
        frappe.throw(
            title="App Installation Failed",
            msg=f"Failed to install app on page {page_id}: {str(e)}"
        )

def refresh_token():
    try:
        meta_config = frappe.get_single("Meta Webhook Config")
        app_id = meta_config.app_id
        app_secret = meta_config.get_password("app_secret")  # Automatically decrypts
        user_token = meta_config.get_password("user_access_token")

        # Check if all fields has data.
        if not app_id or not app_secret or not user_token:
            frappe.throw("App ID, App Secret, and User Token must all be provided in Meta Webhook Config.")

        token_data = is_token_short_lived(meta_config, user_token, app_secret)
        meta_config.user_id = token_data["user_id"]
        if token_data["is_short_lived"]:
            frappe.logger().info('Meta got short lived token, updating...')
            long_token_data = get_long_lived_user_token(meta_config, user_token, app_secret, app_id)
            user_token = long_token_data["access_token"]
        else:
            meta_config.is_token_valid = token_data["is_valid"]
            meta_config.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Failed to Refresh Meta User Token")
        frappe.throw(f"Failed to connect to Meta API: {str(e)}")

# NOTE: By default page access_token are long lived and without expiry.
# def get_long_lived_page_token(doc, user_long_token):
#     try:
#         url = f"{doc.meta_url}/{doc.meta_api_version}/{doc.user_id}/accounts"
#         params = {
#             "access_token": user_long_token,
#         }

#         long_token_response = requests.get(url, params=params)
#         long_token_data = long_token_response.json()

#         if long_token_response.status_code == 200:
#             long_token_data = long_token_response.json()
#             # Extract the Page Access Token
#             data = long_token_data.get("data", [])
#             if len(data) > 0:
#                 page_access_token = data[0].get("access_token")

#             if page_access_token:
#                 return page_access_token
#             else:
#                 raise Exception("Access token not found in the response.")
#         else:
#             # Handle errors
#             error_info = long_token_response.json().get("error", {})
#             error_message = error_info.get("message", "An error occurred.")
#             raise Exception(f"Error {long_token_response.status_code}: {error_message}")

#     except Exception as e:
#         # Handle errors and print them
#         frappe.throw(f"Error retrieving Page Access Token: {str(e)}")
#         raise



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
    page_flow = meta_config.page_flow

    # Check if all fields has data.
    if not app_id or not app_secret or not user_token:
        frappe.throw("App ID, App Secret, and User Token must all be provided in Meta Webhook Config.")

    token_data = is_token_short_lived(meta_config, user_token, app_secret)
    meta_config.user_id = token_data["user_id"]
    if token_data["is_short_lived"]:
        frappe.logger().info('Meta got short lived token, updating...')
        long_token_data = get_long_lived_user_token(meta_config, user_token, app_secret, app_id)
        user_token = long_token_data["access_token"]
    else:
        meta_config.is_token_valid = token_data["is_valid"]
        meta_config.save(ignore_permissions=True)
    frappe.db.commit()
    
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
            'promote_pages', 
            'business_country_code', 
            'business_city', 
            'business_state', 
            'business_zip'
        ])
        
        for ad_account in ad_accounts:
            # Check if the account has associated pages

            # pages = ad_account.get('promote_pages', {}).get("data", [])

            # if len(pages) == 0:
            #     # Skip this ad account if there are no pages
            #     continue
            
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
            pages = ad_account_instance.get_promote_pages(fields=['id', 'name', 'access_token'])

            page_obj = [{"id": page["id"], "name": page["name"], "access_token": page["access_token"]} for page in pages]
            page_ids = [page["id"] for page in page_obj]  # Access as object attribute

            # Add associated pages to child table in Ad Account Config
            for page in page_obj:
                page_id = page["id"]
                page_access_token = page.get("access_token")

                # make entry or update Meta Page DocType
                page_doc = frappe.get_doc("Meta Page", {"page_id": page_id}) if frappe.db.exists("Meta Page", {"page_id": page_id}) else frappe.new_doc("Meta Page")
                page_doc.update({
                    "page_name": page.get("name", "No Name Found"),
                    "page_id": page.get("id"),
                    "page_access_token": page_access_token
                })
                page_doc.save(ignore_permissions=True)

                # If page_flow is enabled, create/update Meta Ads Page Config and get page access token
                if page_flow:
                    # Install app on page and get page access token
                    install_app_to_page(page_access_token, page_id, app_id)
                        
                    # fetch_form_job_id = f"fetch_forms_{ad_account['account_id']}_{page_id}"
                    # existing_job = get_job(fetch_form_job_id)

                    # if existing_job and existing_job.get_status() in ('queued', 'started'):
                    #     frappe.logger().info(f"Job with job_id '{fetch_form_job_id}' is already in the queue or running.")
                    # else:
                    #     frappe.enqueue(
                    #         'onelead.utils.meta.manage_ads.fetch_forms_based_on_page',
                    #         page_id=page_id,
                    #         job_id=fetch_form_job_id,
                    #         enqueue_after_commit=True,
                    #         queue='default' # 300 Sec timeout
                    #     )

            if page_flow:
                # job_id = f"fetch_campaigns_{ad_account['account_id']}"
                # existing_job = get_job(job_id)

                # if existing_job and existing_job.get_status() in ('queued', 'started'):
                #     frappe.logger().info(f"Job with job_id '{job_id}' is already in the queue or running.")
                # else:
                #     frappe.enqueue(
                #         'onelead.utils.meta.manage_ads.fetch_campaigns',
                #         page_id='',
                #         ad_account_id=ad_account['account_id'],
                #         job_id=job_id,
                #         enqueue_after_commit=True,
                #         queue='default' # 300 Sec timeout
                #     )

                # page_flow_fetch_page_and_campaign(page_ids=page_ids, ad_account_id=ad_account["account_id"])
                job_id = f"fetch_data_for_page_flow_{ad_account['account_id']}"
                existing_job = get_job(job_id)

                if existing_job and existing_job.get_status() in ('queued', 'started'):
                    frappe.logger().info(f"Job with job_id '{job_id}' is already in the queue or running.")
                else:
                    frappe.enqueue(
                        'onelead.utils.meta.manage_ads.page_flow_fetch_page_and_campaign',
                        page_ids=page_ids,
                        ad_account_id=ad_account['account_id'],
                        job_id=job_id,
                        queue='long' # 300 Sec timeout
                    )

            # Save the Ad Account
            ad_account_doc.save(ignore_permissions=True)
        
        frappe.db.commit()
        return "Success"

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Meta API Error")
        frappe.throw(f"Failed to connect to Meta API: {str(e)}")


@frappe.whitelist()
def fetch_campaigns(page_id, ad_account_id, page_flow=False):
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
        ad_account = AdAccount(f'act_{ad_account_id}')
        
        # Start fetching campaigns
        params = {'limit': 100 }
        fields = [
            'id', 'name', 'objective', 'status', 'start_time', 'stop_time', 'created_time', 'ads.limit(100){id,name,status,creative{object_story_spec}}'
        ]
        campaigns_cursor = ad_account.get_campaigns(fields=fields, params=params)

        campaign_to_form_dict = {}
        while True:
            # Loop through each campaign and save it in Meta Campaign DocType
            for campaign in campaigns_cursor:
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

                # Process ads associated with this campaign
                ads = campaign.get("ads", [])
                for ad in ads:
                    ad_id = ad["id"]
                    ad_name = ad.get("name", "No Name")
                    ad_status = ad.get("status")
                    
                    # Check if the ad has a lead generation form in its creative
                    has_lead_form = False
                    if ad.get("creative") and ad["creative"].get("object_story_spec"):
                        object_story_spec = ad["creative"].get("object_story_spec")
                        # print("object_story_spec", object_story_spec)
                        call_to_actions = find_call_to_action(object_story_spec.export_all_data())
                        
                        if len(call_to_actions) > 0:
                            for call_to_action in call_to_actions:
                                form_id = call_to_action.get("value", {}).get("lead_gen_form_id")
                                campaign_to_form_dict[form_id] = {
                                    "id": campaign_id,
                                    "status": campaign_status
                                    }

                            has_lead_form = True
                            campaign_doc.set("has_lead_form", has_lead_form)

                    # Prepare ad doc dictionary
                    ad_doc_dict = {
                        "ads_id": ad_id,
                        "ads_name": ad_name,
                        "status": ad_status,
                        "campaign": campaign_id,
                        "has_lead_form": has_lead_form
                    }

                    # Upsert Meta Ads document
                    ad_doc = frappe.get_doc("Meta Ads", {"ads_id": ad_id}) if frappe.db.exists("Meta Ads", {"ads_id": ad_id}) else frappe.new_doc("Meta Ads")
                    ad_doc.update(ad_doc_dict)
                    ad_doc.save(ignore_permissions=True)
                
                campaign_doc.save(ignore_permissions=True)
                # fetch_forms_based_on_selection(campaign_id, '', page_id=page_id)

            # Check for next page
            if campaigns_cursor.load_next_page():
                campaigns_cursor = campaigns_cursor.next()
            else:
                break
        
        frappe.db.commit()

        if page_flow:
            return campaign_to_form_dict
        return "Success"

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Meta API Error")
        frappe.throw(f"Failed to fetch campaigns: {str(e)}")


@frappe.whitelist()
def fetch_forms_based_on_selection(campaign_id, ad_account_id, page_id, ad_id=None):
    # check for user login
    # if not frappe.session.user or frappe.session.user == 'Guest':
    #   frappe.throw("You must be logged in to access this function.")
    
    # check for user access
    # if not frappe.has_permission(doctype="Meta Webhook Config", ptype="read"):
    #     frappe.throw("You do not have permission to access Meta Webhook Config.")
    
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
            ad_data = ad.api_get(fields=['id', 'name', 'adcreatives.limit(100){object_story_spec}'])
            forms = extract_forms_from_ad(ad_data)
        else:
            # Fetch forms based on the campaign
            campaign = Campaign(campaign_id)
            ads_data = campaign.get_ads(fields=['id', 'name', 'adcreatives.limit(100){object_story_spec}'], params={"limit": 100})
            forms = []
            for ad_data in ads_data:
                forms.extend(extract_forms_from_ad(ad_data))
                # print('forms gotten by extracting based on lead_gen_form_id', forms)

        # Store forms in Meta Lead Form and Form List table
        for form in forms:
            # if frappe.db.exists("Meta Lead Form", {"form_id": form["id"]}):
                # print("Form already exists in Meta Lead Form: Form ID, ", form["id"])
            # Create or update Meta Lead Form DocType
            form_doc = frappe.get_doc("Meta Lead Form", {"form_id": form["id"]}) if frappe.db.exists("Meta Lead Form", {"form_id": form["id"]}) else frappe.new_doc("Meta Lead Form")

            form_doc.update({
                # "doctype": "Meta Lead Form",
                "form_id": form["id"],
                # "ads": form["ads_id"]  #commented out, as there needs to be hook for checking Ads Link present before insert
                # TODO: 1c. Remove campaign mapping, once the changes are tested without camapign id.
                "campaign": campaign_id
            })
            form_doc.save(ignore_permissions=True)

        frappe.db.commit()
        return {
            "message": "Forms fetched successfully",
            "data": forms
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Meta API Error")
        frappe.throw(f"Failed to fetch forms: {str(e)}")

def create_meta_ads_page_config_doc(page_id, forms):
    """
    Creates or updates a Meta Ads Page Config document with the given page ID 
    and appends forms to the forms_list child table if provided.

    Args:
        page_id (str): The ID of the Meta Page.
        forms (list): List of forms with details to append to the forms_list.
    """
    try:
        # Fetch existing or create a new Meta Ads Page Config document
        page_config_doc = (frappe.get_doc("Meta Ads Page Config", {"page": page_id}) 
                           if frappe.db.exists("Meta Ads Page Config", {"page": page_id}) 
                           else frappe.new_doc("Meta Ads Page Config"))

        # Update the page and timestamp
        page_config_doc.update({
            "page": page_id,
            "updated_at": frappe.utils.now_datetime()
        })

        # Log the forms for debugging
        frappe.logger().info(f"Forms received for page {page_id}: {forms}")

        if forms and isinstance(forms, list):
            # Clear existing entries in forms_list (optional)
            # page_config_doc.set("forms_list", [])
            existing_form_ids = {entry.meta_lead_form for entry in page_config_doc.forms_list}

            # Append each form to the forms_list child table
            for form in forms:
                form_id = form.get("form_id")
                status = form.get("status")
                # TODO: 1c. Remove campaign mapping, once the changes are tested without camapign id.
                campaign = form.get("campaign", None)
                # created_at = form.get("created_at")

                # Skip if form_id is missing or form is not active 
                if not form_id or status != "ACTIVE":
                    continue 
                
                # print("check if it's value present::: ", form)
                # check if the form has campaign then only add to forms_list
                # TODO: 1c. Remove campaign mapping, once the changes are tested without camapign id.
                if not campaign:
                    continue


                # Check if the form_id already exists in forms_list and Skip if already present
                if form_id in existing_form_ids:
                    continue  

                # Check if created_at is in the year 2024  (removed not in favor of)
                # if created_at:
                #     created_year = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").year
                #     if created_year != 2024:
                #         continue  # Skip if the form was not created in 2024
                
                # print('form........', form)
                page_config_doc.append("forms_list", {
                    "meta_lead_form": form_id,
                    "status": "Not Mapped"
                })

        # Save the document to commit changes
        page_config_doc.save(ignore_permissions=True)
        frappe.msgprint(f"Meta Ads Page Config for page {page_id} successfully updated.")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error Updating Meta Ads Page Config")
        frappe.throw(f"Failed to create/update Meta Ads Page Config: {str(e)}")


@frappe.whitelist()
def fetch_forms_based_on_page(page_id, campaign_to_form_dict=None):
    # Check for user session
    if not frappe.session.user or frappe.session.user == 'Guest':
        frappe.throw("You must be logged in to access this function.")
    
    # Retrieve the Meta Page to access the page token
    try:
        page_doc = frappe.get_doc("Meta Page", page_id)
    except frappe.DoesNotExistError:
        frappe.throw(f"Meta Page with ID {page_id} does not exist.")

    # Retrieve the decrypted page access token
    page_access_token = page_doc.get_password("page_access_token")
    

    if not page_access_token:
        frappe.throw(f"Page Access Token is not available in Meta Page {page_id}. Ensure the page is properly connected.")

    # Initialize Facebook API with the page access token
    FacebookAdsApi.init(access_token=page_access_token)
    
    try:
        # Initialize the Page object
        page = Page(page_id)
        params = {'limit': 100}
        total_fetched = 0
        form_ids = []

        # Fetch the lead generation forms from the current page
        leadgen_forms = page.get_lead_gen_forms(fields=["id", "name", "status", "created_time"], params=params)

        # Paginate through lead generation forms
        while True:
            # Store fetched forms in Meta Lead Form DocType
            for form in leadgen_forms:
                form_id = form["id"]
                form_name = form.get("name", "Unnamed Form")
                status = form.get("status", "")

                # Create or update the form in Meta Lead Form DocType
                form_exists = frappe.db.exists("Meta Lead Form", {"form_id": form_id})
                form_doc = frappe.get_doc("Meta Lead Form", {"form_id": form_id}) if form_exists else frappe.new_doc("Meta Lead Form")
                created_at = form.get("created_time", None)
                if created_at:
                    form_doc.created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S%z").strftime("%Y-%m-%d %H:%M:%S")

                form_doc_payload = {
                    "form_id": form_id,
                    "form_name": form_name,
                    "status": status,
                    "page": page_id,
                }

                if campaign_to_form_dict and campaign_to_form_dict.get(form_id, None):
                    # print("ADD Campaign:::, ", campaign_to_form_dict.get(form_id).get('id'))
                    # TODO: 1c. Remove campaign mapping, once the changes are tested without camapign id.
                    form_doc_payload["campaign"] = campaign_to_form_dict.get(form_id).get('id')
                # print('added to form_ids', form_doc_payload)

                form_doc.update(form_doc_payload)
                form_doc.save(ignore_permissions=True)
                # append with isNew flag
                form_ids.append({"isNew": not form_exists, **form_doc_payload})
                
            # Update total fetched count
            total_fetched += len(leadgen_forms)
            
            # Check if there are more forms to fetch
            if leadgen_forms.load_next_page():
                leadgen_forms = leadgen_forms.next()
            else:
                break  # Exit loop if there are no more pages
        
        frappe.db.commit()
        return form_ids

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Meta API Error")
        frappe.throw(f"Failed to fetch forms: {str(e)}")

@frappe.whitelist()
def page_flow_fetch_page_and_campaign(page_ids, ad_account_id):
    try:
        campaign_to_form_dict = {}
        if ad_account_id:
            campaign_to_form_dict = fetch_campaigns(page_id="", ad_account_id=ad_account_id, page_flow=True)

        # print('Campaign form list', campaign_to_form_dict)
        frappe.logger().info(f"campaign forms list {campaign_to_form_dict}")

        for page_id in page_ids:
            form_ids = fetch_forms_based_on_page(page_id=page_id, campaign_to_form_dict=campaign_to_form_dict)
            create_meta_ads_page_config_doc(page_id, form_ids)

        # fetch_forms_based_on_selection()

    except Exception as e:
        print(e)
        frappe.log_error("page_flow_fetch_page_and_campaign", str(e))

def find_call_to_action(data, depth=0, max_depth=6):
    """Recursively find all call_to_action objects in a nested structure.
        call_to_action can be in different ad object link_data, video_data,
        and these objects may have child_attachments which would have same
        lead_gen_form_id most of the time, but to support edge cases it searches
        recursively.
        give max_depth of 5 to prevent any misuse.
    """
    if depth > max_depth or not data:
        return []
    
    call_to_actions = []
    
    if isinstance(data, dict):
        # If 'call_to_action' is in the current dictionary, add it to the list
        if 'call_to_action' in data:
            call_to_actions.append(data['call_to_action'])
        
        # Recursively search in each value of the dictionary
        for key, value in data.items():
            call_to_actions.extend(find_call_to_action(value, depth + 1, max_depth))
    
    elif isinstance(data, list):
        # Recursively search each item in the list
        for item in data:
            call_to_actions.extend(find_call_to_action(item, depth + 1, max_depth))
    
    return call_to_actions

def extract_forms_from_ad(ad_data):
    """Extract forms from the ad creatives in the ad data."""
    forms = []
    seen_form_ids = set()

    creatives = ad_data.get("adcreatives", {}).get("data", [])

    for creative in creatives:
        object_story_spec = creative.get("object_story_spec", {})
        call_to_actions = find_call_to_action(object_story_spec)

        for call_to_action in call_to_actions:
            form_id = call_to_action.get("value", {}).get("lead_gen_form_id")

            # maintain set for unique form IDs
            if form_id and form_id not in seen_form_ids:
                forms.append({
                    "id": form_id,
                    "name": call_to_action.get("type", "no type")
                })
                seen_form_ids.add(form_id)

    return forms

@frappe.whitelist()
def fetch_form_details(doc, method):
    # Check if Form ID and Campaign are provided
    if not doc.form_id:
        frappe.throw("Form ID is required to fetch form details, with fetch_form_dtails")
    
    if doc.question_fetched and not doc.force_refresh:
        return
    
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
            'id', 'name', 'status', 'locale', 'questions', 'created_time'
        ])
        
        # Populate form details in the Meta Lead Form document
        doc.form_name = form_data.get("name", "Unknown")
        doc.status = form_data.get("status", "INACTIVE")
        doc.locale = form_data.get("locale", "en_US")
        created_at = form_data.get("created_time", None)
        if created_at:
            doc.created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S%z").strftime("%Y-%m-%d %H:%M:%S")

        # Convert existing meta fields in mapping to a set for easy checking
        existing_meta_fields = {entry.meta_field for entry in doc.mapping}

        # Add questions to the child table
        questions = form_data.get("questions", [])
        for question in questions:
            meta_field = question.get("key", '')
            if meta_field and meta_field not in existing_meta_fields:
                doc.append("mapping", {
                    "meta_field": meta_field,
                    "lead_doctype_field": "", 
                    "default_value": "",      
                    "formatting_function": ""
                })
        # for question in questions:
        #     doc.append("mapping", {
        #         "meta_field": question.get("key", ''),
        #         "lead_doctype_field": "", 
        #         "default_value": "",      
        #         "formatting_function": ""
        #     })
        doc.force_refresh = 0
        doc.question_fetched = 1
        return

    except Exception as e:
        print(e)
        frappe.log_error(frappe.get_traceback(), "Meta API Error")
        frappe.throw(f"Failed to fetch form details: {str(e)}")
