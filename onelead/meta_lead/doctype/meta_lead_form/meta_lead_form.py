# Copyright (c) 2024, Redsoftware Solutions and contributors
# For license information, please see license.txt

import frappe
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