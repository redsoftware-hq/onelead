// Copyright (c) 2024, Redsoftware Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Google Ad Campaign Config", {
  lead_doctype: function(frm) {
    if (frm.doc.lead_doctype) {
      frappe.call({
        method: 'frappe.client.get',
        args: {
          doctype: 'DocType',
          name: frm.doc.lead_doctype
        },
        callback: function(response) {
          let lead_doctype_meta = response.message;
          if (lead_doctype_meta) {
            frm.clear_table('mapping');

            lead_doctype_meta.fields.forEach((field) => {
              if (field.reqd) {
                console.log(field)
                let row = frm.add_child('mapping');
                row.ad_form_field_key = '';
                row.lead_doctype_field = field.fieldname;
                row.field_type = field.fieldtype;
              }
            });

            frm.refresh_field('mapping');
          }
        }
      })
    }
  }
});

