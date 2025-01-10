# Copyright (c) 2024, Redsoftware Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from onelead.utils.meta.manage_ads import fetch_forms_based_on_page
# from frappe.utils.nestedset import NestedSet


class MetaAdsPageConfig(Document):
	pass
	#  def after_insert(self):
	# 		# Trigger fetching ad forms after Meta Ads Page Config is created
	# 		forms = fetch_forms_based_on_page(self.page)
	
	# 		print("forms fetched from backend... {forms}")
	# 		if forms and isinstance(forms, list):
	# 				# Clear existing entries in form_list if any (optional)
	# 				self.forms_list = []

	# 				# Populate form_list child table with fetched form IDs
	# 				for form in forms:
	# 						frappe.msgprint(f"form fetched for list entry.... {form}")
	# 						self.append("forms_list", {
	# 								"meta_lead_form": form.get("form_id"),
	# 								"status": "Not Mapped"
	# 						})
					
	# 				# Save the document to commit changes
	# 				self.save(ignore_permissions=True)
