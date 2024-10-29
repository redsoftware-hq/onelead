// Copyright (c) 2024, Redsoftware Solutions and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Meta Ads Webhook Config", {
// 	refresh(frm) {

// 	},
// });

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
  },

  refresh: function (frm) {
    // Only show the button if ad_account and page are set
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
  },

  before_save: function (frm) {
    // Validate the presence of required fields before saving
    if (!frm.doc.campaign || !frm.doc.ad_account || !frm.doc.page) {
      frappe.throw("Please select a campaign, ad account, and page before saving.");
    }

    // Trigger function to fetch forms after saving
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
          frappe.msgprint("Forms fetched successfully.");
          
          frm.clear_table("forms_list");

          // Append each fetched form to the Form List child table
          response.data.forEach(function (form) {
            let row = frm.add_child("forms_list");
            row.meta_lead_form = form.id;
            row.status = "Not Mapped"
          });

          // Refresh the child table field to show new entries
          frm.refresh_field("form_list");
        }
      }
    });
  }
});
