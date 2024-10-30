// Copyright (c) 2024, Redsoftware Solutions and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Meta Ads Webhook Config", {
// 	refresh(frm) {

// 	},
// });

// Copyright (c) 2024, Redsoftware Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Meta Ads Webhook Config', {
  onload: function (frm) {
    // Hide or show Ads field based on the checkbox value
    frm.toggle_display('ads', frm.doc.config_based_on_ad_name);
  },

  config_based_on_ad_name: function (frm) {
    // Show or hide Ads field based on checkbox selection
    frm.toggle_display('ads', frm.doc.config_based_on_ad_name);
  },

  refresh: function (frm) {
    // Ensure Ads field visibility is correct on load
    frm.toggle_display('ads', frm.doc.config_based_on_ad_name);

    // Add custom "Fetch Campaigns" button if required fields are set
    if (frm.doc.page && frm.doc.ad_account) {
      frm.add_custom_button(__('Fetch Campaigns'), function () {
        frappe.call({
          method: 'onelead.utils.meta.manage_ads.fetch_campaigns',
          args: {
            page_id: frm.doc.page,
            ad_account_id: frm.doc.ad_account
          },
          callback: function (response) {
            if (response.message) {
              frappe.msgprint(__('Campaigns fetched and saved successfully.'));
            }
          }
        });
      });
    }

    // Add custom "Fetch Forms" button if required fields are set
    if (frm.doc.campaign && frm.doc.ad_account && frm.doc.page) {
      frm.add_custom_button(__('Fetch Forms'), function () {
        frappe.call({
          method: "onelead.utils.meta.manage_ads.fetch_forms_based_on_selection",
          args: {
            campaign_id: frm.doc.campaign,
            ad_account_id: frm.doc.ad_account,
            page_id: frm.doc.page,
            ad_id: frm.doc.ads || null  // Pass ad_id only if available
          },
          callback: function (response) {
            if (response.message) {
              frappe.msgprint({
                title: __('Forms Fetch Status'),
                message: __('Forms fetched successfully.'),
                indicator: 'green'
              });

              frm.clear_table("forms_list");

              // Append each fetched form to the Form List child table
              if (response.message.data && response.message.data.length > 0) {
                response.message.data.forEach(function (form) {
                  let row = frm.add_child("forms_list");
                  row.meta_lead_form = form.id;
                  row.status = "Not Mapped";
                });

                // Refresh the child table field to show new entries
                frm.refresh_field("forms_list");
              } else {
                frappe.msgprint({
                  title: __('No Forms Found'),
                  message: __('No forms were found for the given campaign, account, and page.'),
                  indicator: 'orange'
                });
              }
            } else {
              frappe.msgprint({
                title: __('Error'),
                message: __('Failed to fetch forms or no forms returned.'),
                indicator: 'red'
              });
            }
          }
        });
      });
    }

    // frm.doc["forms_list"].grid.add_custom_button(__("Quick Map"), function() {
    //   alert("button")
    // })
    // frm.fields_dict["forms_list"].grid.add_custom_button(__('Hello'),
    //   function () {
    //     frappe.msgprint(__("Hello"));
    //   });
    // frm.fields_dict["forms_list"].grid.grid_buttons.find('.btn-custom').removeClass('btn-default').addClass('btn-primary');

  }
});

frappe.ui.form.on("Meta Campaign Form List", {
  quick_map: function (frm, cdt, cdn) {
    console.log("Quick Map button clicked");
    let row = locals[cdt][cdn];
    //  mandatory fieds of lead_doctype for validation
    let mandatory_fields = []; 

    if (!row.meta_lead_form) {
      frappe.msgprint(__('Please select a Meta Lead Form before mapping.'));
      return;
    }

    if (row) {
      console.log("Row data:", row);
    } else {
      console.log("Row data not found");
    }


    // Fetch DocType "Meta Lead Form" data, to populate mapping form.
    frappe.call({
      method: 'frappe.client.get',
      args: {
        doctype: 'Meta Lead Form',
        name: row.meta_lead_form
      },
      callback: function (r) {
        if (r.message) {
          const metaLeadForm = r.message;
          const mappings = metaLeadForm.mapping || [];

          console.log("mapping...", mappings)

          // Dialog to display mappings
          let d = new frappe.ui.Dialog({
            size: 'extra-large',
            title: 'Quick Map Lead Fields',
            fields: [
              {
                label: 'Lead DocType Reference',
                fieldname: 'lead_doctype',
                fieldtype: 'Link',
                options: 'DocType',
                default: metaLeadForm.lead_doctype_reference,
                reqd: 1,
                change: function () {
                  let lead_doctype = d.get_value('lead_doctype');
                  if (lead_doctype) {
                    // Fetch fields from the selected Lead DocType
                    frappe.call({
                      method: 'frappe.client.get',
                      args: {
                        doctype: 'DocType',
                        name: lead_doctype
                      },
                      callback: function (r) {
                        if (r.message) {
                          // Filter fields based on mappable field types (Data, Link, etc.)
                          let mappable_fields = r.message.fields
                            .filter(field => ['Data', 'Phone', 'Link', 'Select', 'Int', 'Float', 'Date'].includes(field.fieldtype))
                            .map(field => field.fieldname);

                          // Get mandatory fields
                          mandatory_fields = r.message.fields
                            .filter(field => field.reqd)
                            .map(field => field.fieldname);

                          // Update lead_doctype_field options in the mapping table
                          d.fields_dict.mapping.grid.update_docfield_property(
                            'lead_doctype_field', 'options', mappable_fields.join('\n')
                          );
                          d.fields_dict.mapping.grid.refresh();  // Refresh to apply new options
                        }
                      }
                    });
                  }
                }
              },
              {
                fieldtype: 'Section Break',
                label: 'Field Mappings'
              },
              {
                fieldname: 'mapping',
                label: 'Mapping Table',
                fieldtype: 'Table',
                options: 'Meta Lead Form Mapping', // Fields Mapping DocType
                fields: [
                  {
                    label: 'Meta Field',
                    fieldname: 'meta_field',
                    fieldtype: 'Data',
                    in_list_view: 1
                  },
                  {
                    label: 'Lead DocType Field',
                    fieldname: 'lead_doctype_field',
                    fieldtype: 'Select',
                    in_list_view: 1
                  },
                  {
                    label: 'Default Value',
                    fieldname: 'default_value',
                    fieldtype: 'Data',
                    in_list_view: 1
                  },
                  {
                    label: 'Formatting Function',
                    fieldname: 'formatting_function',
                    fieldtype: 'Code',
                    in_list_view: 1
                  }
                ]
              }
            ],
            primary_action_label: 'Save Mappings',
            primary_action: function (data) {
              // Validation for mandatory fields in the mapping
              let missing_fields = mandatory_fields.filter(mandatory_field =>
                !data.mapping.some(mapping => mapping.lead_doctype_field === mandatory_field)
              );

              if (missing_fields.length > 0) {
                frappe.show_alert({
                  message: __('Warning: The following mandatory fields are missing in the mapping table: ') +
                    missing_fields.join(', '),
                  indicator: 'orange'
                }, 10); // Longer display of Warning as feature is WIP and don't want to block by Error.

                // Stop the save action
                // return;
              }

              // Validations for mapping table
              let validation_failed = false;

              data.mapping.forEach(mapping => {
                // Only validate rows where `lead_doctype_field` is populated
                if (mapping.lead_doctype_field) {
                  if (!mapping.meta_field && !mapping.default_value) {
                    validation_failed = true;
                    frappe.msgprint(__('Each Lead DocType Field with a value must have either a Meta Field or a Default Value.'));
                  }
                }
              });

              if (validation_failed) {
                return;  // Stop the save action if validation fails
              }

              console.log("Mapped data before update:", data.mapping);

              // metaLeadForm.mapping = data.mapping;
              metaLeadForm.mapping = []

              // Add each entry from `data.mapping` to `latest_meta_lead_form.mapping`
              data.mapping.forEach(mapping_entry => {
                // Create a new mapping row object
                const child_row = {
                  meta_field: mapping_entry.meta_field,
                  lead_doctype_field: mapping_entry.lead_doctype_field,
                  default_value: mapping_entry.default_value,
                  formatting_function: mapping_entry.formatting_function
                };

                // Push the new row directly into the `mapping` array
                metaLeadForm.mapping.push(child_row);
              });
              metaLeadForm.lead_doctype_reference = data.lead_doctype;

              // Save the updated document
              frappe.call({
                method: 'frappe.client.save',
                args: {
                  doc: metaLeadForm
                },
                callback: function (save_response) {
                  if (save_response.message) {
                    frappe.msgprint(__('Fields mapped and saved successfully.'));
                    row.status = 'Mapped';
                    frm.refresh_field('forms_list');
                  }
                }
              });

              // Update mappings and lead doctype in "Meta Lead Form"
              // frappe.call({
              //   method: 'frappe.client.get',
              //   args: {
              //     doctype: 'Meta Lead Form',
              //     name: metaLeadForm.name  // row.meta_lead_form
              //   },
              //   callback: function (refetch_response) {
              //     if (refetch_response.message) {
              //       let latest_meta_lead_form = refetch_response.message;

              //       console.log(data.mapping)

              //       // Update only necessary fields
              //       latest_meta_lead_form.lead_doctype_reference = data.lead_doctype;
              //       latest_meta_lead_form.mapping = data.mapping;

              //       // Save the updated document
              //       frappe.call({
              //         method: 'frappe.client.save',
              //         args: {
              //           doc: latest_meta_lead_form
              //         },
              //         callback: function (save_response) {
              //           if (save_response.message) {
              //             frappe.msgprint(__('Fields mapped and saved successfully.'));
              //             row.status = 'Mapped';
              //             frm.refresh_field('forms_list');
              //           }
              //         }
              //       });
              //     } else {
              //       frappe.msgprint(__('Failed to fetch the latest document. Please try again.'));
              //     }
              //   }
              // });


              d.hide();
            }
          });

          console.log(d.fields_dict.mapping.grid.doctype)
          // populate mapping table with existing data.
          const mappingTable = d.fields_dict.mapping.grid.get_data(); 

          console.log("Mapping Table", mappingTable)

          d.fields_dict.mapping.df.data = mappings.map(mapping => ({
            meta_field: mapping.meta_field,
            lead_doctype_field: mapping.lead_doctype_field,
            default_value: mapping.default_value,
            formatting_function: mapping.formatting_function
          }));

          d.fields_dict.mapping.grid.refresh();  // Refresh the table in the dialog
          d.show();
        } else {
          frappe.msgprint(__('Meta Lead Form not found.'));
        }
      }
    });

  }
})
