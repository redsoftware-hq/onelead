# Copyright (c) 2024, Redsoftware Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document



class MetaLeadForm(Document):
    def validate(self):
        self.validate_mapping_table()

    def validate_mapping_table(self):
        """Ensures each row in the mapping table has either a meta_field or default_value if lead_doctype_field is populated."""
        for mapping in self.mapping:
            if mapping.lead_doctype_field:  # Only validate rows where lead_doctype_field is set
                if not mapping.meta_field and not mapping.default_value:
                    frappe.throw(
                        _("Each Lead DocType Field with a value in the mapping table must have either a Meta Field or a Default Value."),
                        title=_("Validation Error")
                    )
        
    def on_update(self):
        """
        After insert, if `assign_to` or `assignee_doctype` are changed and a campaign is linked,
        update the linked campaign with the new values.
        """
        # TODO: 1a - 1c: Remove the logic in light of the new M:M relationship between `Meta Lead Form` and `Meta Campaign` 
        if self.campaign:
            # Fetch the linked campaign
            campaign = frappe.get_doc("Meta Campaign", self.campaign)

            # Check if `assign_to` or `assignee_doctype` are different and update
            fields_to_update = {}
            if campaign.assign_to != self.assign_to or campaign.assignee_doctype != self.assignee_doctype:
                fields_to_update["assign_to"] = self.assign_to
                fields_to_update["assignee_doctype"] = self.assignee_doctype

            if fields_to_update:
                # Update the campaign only if there's a change
                campaign.update(fields_to_update)
                campaign.save(ignore_permissions=True)  # Save without checking permissions
                frappe.msgprint(
                    _("Linked campaign {0} updated with new assignee details.").format(campaign.name),
                    alert=True
                )