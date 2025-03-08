frappe.listview_settings["Meta Webhook Lead Logs"] = {
  onload: function (listview) {
    listview.page.add_inner_button(__("Process Leads"), function () {
      // Get all checked (selected) items in the list
      let selected_docs = listview.get_checked_items();
      if (!selected_docs.length) {
        frappe.msgprint(__("Please select at least one record to process."));
        return;
      }

      // Convert each item into just the name string
      let docnames = selected_docs.map(doc => doc.name);

      // Call server-side method
      frappe.call({
        method: "onelead.utils.meta.manage_leads.bulk_manual_retry_lead_processing",
        args: {
          docnames: docnames
        },
        callback: function (r) {
          if (!r.exc) {
            frappe.msgprint(__("Processing initiated. Results will be logged in each document's timeline or error_message."));
            // Optionally, refresh the list or do something else
            listview.refresh();
          }
        }
      });
    });
  }
};
