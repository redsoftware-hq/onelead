// Copyright (c) 2024, Redsoftware Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Meta Webhook Lead Logs", {
	refresh(frm) {
		if (!frm.doc.lead_doc_reference && frm.doc.processing_status !== "Processed") {
			frm.add_custom_button(__('Process Lead Again'), function() {
				frappe.call({
					method: "onelead.utils.meta.manage_leads.manual_retry_lead_processing",
					args: {
						docname: frm.doc.name,
					},
					callback: function(r) {
						if (r.message) {
							frappe.msgprint(__('Lead processed successfully.'));
							frm.reload_doc();
						} else {
							frappe.msgprint(__('Failed to process lead.'));
						}
					}
				});
			});
		}
	}
});
