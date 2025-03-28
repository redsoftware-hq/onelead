// Copyright (c) 2024, Redsoftware Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Meta Ads Page Config", {
  setup: function (frm) {
    frm.fields_dict['forms_list'].grid.get_field('meta_lead_form').get_query = function () {
      let added_forms = frm.doc.forms_list.map(row => row.meta_lead_form).filter(f => f);
      return {
        filters: [
          ['Meta Lead Form', 'name', 'not in', added_forms],
          ['Meta Lead Form', 'page', '=', frm.doc.page]
        ]
      };
    };
  },

  onload: function (frm) {
    // Hide or show Assignee fields based on the checkbox value
    frm.toggle_display('assignee_doctype', frm.doc.lead_assign);
    frm.toggle_display('assign_to', frm.doc.lead_assign);
  },

  lead_assign: function (frm) {
    // Show or hide Assignee fields based on checkbox selection
    frm.toggle_display('assignee_doctype', frm.doc.lead_assign);
    frm.toggle_display('assign_to', frm.doc.lead_assign);
  },

  refresh(frm) {
    // Add a custom button for Populate Forms
    frm.add_custom_button(__('Populate Forms'), function () {
      if (!frm.doc.page) {
        frappe.msgprint(__('Please select a Page before populating forms.'));
        return;
      }

      frappe.call({
        method: "onelead.utils.meta.manage_ads.get_latest_forms_for_page",
        args: {
          page_id: frm.doc.page
        },
        btn: $('.primary-action'),
        freeze: true,
        callback: function (response) {
          // frappe.msgprint(f"Forms fetched for page {page_id}: {', '.join(form_names)}")
          console.log(response)
          if (response.message.length == 0) {
            frappe.msgprint(__('No forms to fetch from Meta'))
          } else {
            frappe.msgprint(__(`Forms fetched for page ${frm.doc.page}: ${response.message.join(',')}`))
          }
        },
        error: function (err) {
          frappe.msgpring(__(`Failed to Fetch forms from Meta, error: ${err}`))
        }
      })
      .then(r => {
        // Fetch forms linked to the selected page
        frappe.call({
          method: "frappe.client.get_list",
          args: {
            doctype: "Meta Lead Form",
            filters: {
              page: frm.doc.page, // Match the Page ID
              status: "ACTIVE", // Form should be active
              // 1a. remove campaign in light of M:M relation of campaign and form
              // campaign: ["is", "set"] // Ensure a campaign is assigned
            },
            // TODO: 1a. remove campaign in light of M:M relation of campaign and form
            fields: ["name", "form_name", "campaign"]
          },
          btn: $('.primary-action'),
          freeze: true,
          callback: function (response) {
            if (response.message.length > 0) {
              const activeForms = response.message;
              let upsertedForms = 0;
  
              // Loop through the retrieved forms
              activeForms.forEach(form => {
                // Check if the campaign is active
                // TODO: 1a. Remove the logic of campaign in light of M;M relation.
                frappe.call({
                  method: "frappe.client.get",
                  args: {
                    doctype: "Meta Campaign",
                    name: form.campaign
                  },
                  callback: function (campaignResponse) {
                    const campaign = campaignResponse.message;
                    if (campaign && campaign.status === "ACTIVE") {
                      // Add or update the form in the mapping table
                      const existingForm = frm.doc.forms_list.find(row => row.meta_lead_form === form.name);
                      if (!existingForm) {
                        // Add new row
                        const newRow = frm.add_child("forms_list");
                        newRow.meta_lead_form = form.name;
                        newRow.campaign = form.campaign;
                        upsertedForms++;
                      } else {
                        // Update existing row if necessary
                        existingForm.campaign = form.campaign;
                      }
  
                      // Refresh the child table field
                      frm.refresh_field("forms_list");
                    }
                  }
                });
              });
  
              frappe.msgprint(__(`${upsertedForms} forms have been populated and updated successfully.`));
            } else {
              frappe.msgprint(__('No forms found matching the criteria.'));
            }
          }
        });
      })
    });


    // Refresh query every time a row is added or removed
    // frm.fields_dict['forms_list'].grid.grid_events.on('add', function () {
    //   frm.fields_dict['forms_list'].grid.get_field('meta_lead_form').get_query = function () {
    //     let added_forms = frm.doc.forms_list.map(row => row.meta_lead_form).filter(f => f);
    //     return {
    //       filters: [
    //         ['Meta Lead Form', 'name', 'not in', added_forms]
    //       ]
    //     };
    //   };
    // });

    // frm.fields_dict['forms_list'].grid.grid_events.on('remove', function () {
    //   frm.fields_dict['forms_list'].grid.get_field('meta_lead_form').get_query = function () {
    //     let added_forms = frm.doc.forms_list.map(row => row.meta_lead_form).filter(f => f);
    //     return {
    //       filters: [
    //         ['Meta Lead Form', 'name', 'not in', added_forms]
    //       ]
    //     };
    //   };
    // });
  }
});


frappe.ui.form.on("Meta Campaign Form List", {
  quick_map: function (frm, cdt, cdn) {
    // let formatting_function_options = '\n'
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


    frappe.call({
      method: "onelead.utils.formatting_functions.get_function_names",
      callback: function (response) {
        formatting_function_options = response.message || [];
        console.log('form_fun', formatting_function_options)
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
                    // Try to take form lead doc ref first, if not found then from parent lead doc ref. 
                    default: metaLeadForm.lead_doctype_reference || frm.doc.lead_doctype_reference,
                    // reqd: 1,
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
                                .filter(field => ['Data', 'Phone', 'Link', 'Select', 'Int', 'Date'].includes(field.fieldtype))
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
                    cannot_add_rows: false,  // Allow adding new rows
                    in_place_edit: false,  // Allow inline editing
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
                        fieldtype: 'Select',
                        in_list_view: 1,
                        options: formatting_function_options
                      },
                      {
                        label: 'Function Parameters',
                        fieldname: 'function_parameters',
                        fieldtype: 'Code',
                      }
                    ]
                  },
                  {
                    fieldtype: 'Section Break',
                    label: 'Lead Assign'
                  },
                  {
                    default: metaLeadForm.assignee_doctype || frm.doc.assignee_doctype || "User",
                    fieldname: "assignee_doctype",
                    fieldtype: "Link",
                    label: "Assignee Doctype",
                    options: "DocType"
                  },
                  {
                    fieldname: "column_break_1",
                    fieldtype: "Column Break"
                  },
                  {
                    default: metaLeadForm.assign_to || frm.doc.assign_to,
                    fieldname: "assign_to",
                    fieldtype: "Dynamic Link",
                    label: "Assign To",
                    options: "assignee_doctype"
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
    
                  if (!data.assign_to) {
                    validation_failed = true;
                    frappe.msgprint(__('Please complete Lead Assign section'))
                  }
    
                  if (validation_failed) {
                    return;  // Stop the save action if validation fails
                  }
    
                  console.log("Mapped data before update:", data.mapping);
                  
                  metaLeadForm.assignee_doctype = data.assignee_doctype;
                  metaLeadForm.assign_to = data.assign_to;
                  
                  // metaLeadForm.mapping = data.mapping;
                  metaLeadForm.mapping = []
    
                  // Add each entry from `data.mapping` to `latest_meta_lead_form.mapping`
                  data.mapping.forEach(mapping_entry => {
                    // Create a new mapping row object
                    const child_row = {
                      meta_field: mapping_entry.meta_field,
                      lead_doctype_field: mapping_entry.lead_doctype_field,
                      default_value: mapping_entry.default_value,
                      formatting_function: mapping_entry.formatting_function,
                      function_parameters: mapping_entry.function_parameters
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
                formatting_function: mapping.formatting_function,
                function_parameters: mapping.function_parameters
              }));
    
              d.fields_dict.mapping.grid.refresh();  // Refresh the table in the dialog
              d.show();
            } else {
              frappe.msgprint(__('Meta Lead Form not found.'));
            }
          }
        });
      }
    });

  }
})
