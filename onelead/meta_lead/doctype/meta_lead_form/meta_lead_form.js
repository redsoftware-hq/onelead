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
      })
        .attr('title', __('Create a new Campaign document using fields from this form, If not, this will be created automatically when leads are received.'));

    }

    if (!frm.doc.ads) {
      // ----- NEW BUTTON: Create Ads -----
      frm.add_custom_button(__('Create Ads'), function () {
        // 1. Generate an Ads ID and Ads Name
        const adsId = (frm.doc.form_name || "Ad") + "_" + (frm.doc.form_id || "");
        const adsName = frm.doc.form_name || `Ads for ${frm.doc.form_id}`;

        // 2. Validate necessary fields
        if (!frm.doc.campaign) {
          frappe.msgprint(__('Please link a Campaign first before creating Ads'));
          return;
        }

        // 3. Check if a Meta Ads doc with the derived Ads ID already exists
        frappe.call({
          method: "frappe.client.get_list",
          args: {
            doctype: "Meta Ads",
            filters: { ads_id: adsId },
            fields: ["name", "ads_name"]
          },
          callback: function (r) {
            if (r.message && r.message.length > 0) {
              // Found an existing Ads doc
              const existingAds = r.message[0];
              frappe.msgprint(__("Ads already exists: ") + existingAds.ads_name);

              // Link that Ads doc to this form (assuming you have a 'meta_ads' link field or similar)
              frm.set_value("meta_ads", existingAds.name);
              frm.save();
            } else {
              // 4. Insert a new Meta Ads record
              frappe.call({
                method: "frappe.client.insert",
                args: {
                  doc: {
                    doctype: "Meta Ads",
                    ads_id: adsId,
                    ads_name: adsName,
                    status: frm.doc.status,
                    campaign: frm.doc.campaign,
                    has_lead_form: 1 // or whatever your checkbox field is named
                  }
                },
                callback: function (res) {
                  if (!res.exc) {
                    const adsDoc = res.message;
                    frappe.msgprint(__("New Ads created: ") + adsDoc.ads_name);

                    // Link the newly created Ads to this form
                    frm.set_value("meta_ads", adsDoc.name);
                    frm.save();
                  }
                }
              });
            }
          }
        });
      })
      .attr('title', __('Create a new Meta Ads document using fields from this form, If not, this will be created automatically when leads are received.'));
    }
  }
});
