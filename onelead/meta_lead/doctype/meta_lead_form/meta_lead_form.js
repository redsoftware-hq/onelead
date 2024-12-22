// Copyright (c) 2024, Redsoftware Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Meta Lead Form", {
  refresh(frm) {
    // Add a custom button
    if (!frm.doc.campaign) {
      frm.add_custom_button(__('Create Campaign'), async function () {
        // Generate campaign ID
        const campaignId = frm.doc.form_name.replace(/\s+/g, '_') + "_" + frm.doc.form_id;
        const campaignName = frm.doc.form_name || `Campaign for ${frm.doc.form_id}`;
        const campaignObjective = "OUTCOME_LEADS"; // Default objective

        // Validate necessary fields
        if (!frm.doc.page) {
          frappe.msgprint(__('Please select a Page before creating or linking a campaign.'));
          return;
        }

        // Check if a campaign with the generated campaign_id already exists
        frappe.call({
          method: "frappe.client.get_list",
          args: {
            doctype: "Meta Campaign",
            filters: {
              campaign_id: campaignId
            },
            fields: ["name", "campaign_name"]
          },
          callback: function (response) {
            if (response.message.length > 0) {
              // Campaign exists - link it to the form
              const existingCampaign = response.message[0];
              frappe.msgprint(__('Campaign already exists: ') + existingCampaign.campaign_name);

              // Link the existing campaign to the Meta Lead Form
              frm.set_value("campaign", existingCampaign.name);
              frm.save();
            } else {
              // Campaign does not exist - create a new one
              frappe.call({
                method: "frappe.client.insert",
                args: {
                  doc: {
                    doctype: "Meta Campaign",
                    campaign_id: campaignId,
                    campaign_name: campaignName,
                    campaign_objective: campaignObjective,
                    status: "ACTIVE",
                    has_lead_form: 1,
                    self_created: 1,
                    assignee_doctype: frm.doc.assignee_doctype,
                    assign_to: frm.doc.assign_to
                  }
                },
                callback: function (response) {
                  if (!response.exc) {
                    const campaignDoc = response.message;
                    frappe.msgprint(__('Campaign Created: ') + campaignDoc.campaign_name);

                    // Link the newly created campaign to the Meta Lead Form
                    frm.set_value("campaign", campaignDoc.name);
                    frm.save();
                  }
                }
              });
            }
          }
        });
      });
    }
  }
});
