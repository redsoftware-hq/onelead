# Copyright (c) 2024, Redsoftware Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GoogleAdCampaignConfig(Document):

	def validate(self):
		lead_doctype = self.lead_doctype

		if not lead_doctype:
			frappe.throw("Please select a Lead Doctype.")

		lead_meta = frappe.get_meta(lead_doctype)

		for mapping in self.mapping:
			lead_field = mapping.lead_doctype_field

			if not lead_meta.has_field(lead_field):
				frappe.throw(f"Field '{lead_field}' does not exist in the Lead Doctype '{lead_doctype}'.")

			field_type = lead_meta.get_field(lead_field).fieldtype
			mapping.field_type = field_type

			if not mapping.ad_form_field_key:
				frappe.throw(f"The Ad Form Field Key cannot be empty for '{lead_field}' in mapping.")

		for constant in self.constants:
			lead_field = constant.lead_doctype_field
			
			# Check if the field exists in the Lead Doctype
			field_meta = lead_meta.get_field(lead_field)
			if not field_meta:
					frappe.throw(f"Field '{lead_field}' does not exist in the Lead Doctype '{lead_doctype}'.")
			
			field_type = field_meta.fieldtype
			constant_value = constant.constant_value
			
			# Validate and convert the constant value based on the field type
			try:
					if field_type in ['Int', 'Currency', 'Float']:
							# Convert to the appropriate numeric type
							constant.constant_value = float(constant_value) if field_type == 'Float' else int(constant_value)
					elif field_type == 'Date':
							# Validate if the value is a valid date
							constant.constant_value = frappe.utils.getdate(constant_value)
					elif field_type == 'Datetime':
							# Validate if the value is a valid datetime
							constant.constant_value = frappe.utils.get_datetime(constant_value)
					elif field_type == 'Check':
							# Convert to 0 or 1 (assuming it's a checkbox)
							constant.constant_value = 1 if constant_value.lower() in ['1', 'true', 'yes'] else 0
					elif field_type == 'Select' and field_meta.options:
							# Validate against the allowed options
							if constant_value not in field_meta.options.split('\n'):
									frappe.throw(f"Invalid value '{constant_value}' for field '{lead_field}'. Allowed options are: {field_meta.options}")
					elif field_type == 'Link':
							# Validate that the link exists in the referenced Doctype
							if not frappe.db.exists(field_meta.options, constant_value):
									frappe.throw(f"Invalid link value '{constant_value}' for field '{lead_field}'. It must exist in the '{field_meta.options}' doctype.")
					# Other field types can be handled similarly
			except Exception as e:
					frappe.throw(f"Invalid constant value '{constant_value}' for field '{lead_field}' of type '{field_type}'. Error: {str(e)}")

			# Update the field type in the child table (for informational purposes)
			constant.field_type = field_type
