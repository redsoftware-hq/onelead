// Copyright (c) 2024, Redsoftware Solutions and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Meta Webhook Config", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('Meta Webhook Config', {
  connect_facebook: function (frm) {
    frappe.call({
      method: 'onelead.utils.meta.manage_ads.get_adaccounts',
      callback: function (response) {
        console.log(response)
        if (response.message) {
          frappe.msgprint("Ad Accounts and Pages fetched successfully!");
          frm.reload_doc();
        }
      }
    });
  }
});
