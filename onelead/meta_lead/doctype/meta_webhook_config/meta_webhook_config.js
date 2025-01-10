// Copyright (c) 2024, Redsoftware Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on('Meta Webhook Config', {
  refresh: function (frm) {
    // Apply initial styling to the button
    applyButtonStyle(frm, 'enabled', 'Connect Facebook');

    // Check if any jobs are running or queued
    frappe.call({
      method: 'onelead.utils.utils.check_jobs_running',
      callback: function (response) {
        console.log(response)
        if (response.message) {
          // Disable the button if jobs are running
          applyButtonStyle(frm, 'disabled', 'Processing...');
        } else {
          // Enable the button if no jobs are running
          applyButtonStyle(frm, 'enabled', 'Connect Facebook');
        }
      }
    });
  },
  connect_facebook: function (frm) {
    // Disable the button and show "Processing..." at the start of the function
    applyButtonStyle(frm, 'disabled', 'Processing...');

    frappe.call({
      method: 'onelead.utils.meta.manage_ads.get_adaccounts',
      callback: function (response) {
        console.log(response);
        if (response.message) {
          frappe.msgprint("Ad Accounts and Pages fetched successfully!");
          frm.reload_doc();
        }
        // Re-enable the button after completion
        // applyButtonStyle(frm, 'enabled', 'Connect Facebook');
      },
      error: function () {
        // Re-enable the button in case of error
        applyButtonStyle(frm, 'enabled', 'Connect Facebook');
        frappe.msgprint("There was an error connecting to Facebook.");
      }
    });
  }
});

// Helper function to apply button styles based on the state
function applyButtonStyle(frm, state, text) {
  const button = frm.fields_dict.connect_facebook.$input;
  button.prop('disabled', state === 'disabled').text(text);

  // Apply inline styles based on the button state
  if (state === 'disabled') {
    button.css({
      "background-color": "#fff7d3",
      "color": "#ab6e05",
      "box-shadow": "0 0 10px rgba(255, 204, 0, 0.6)", // Glow effect
      "animation": "pulse 1.5s infinite",
      "border-radius": "8px",
      "border": "1px #fff0b0 solid",
      "cursor": "not-allowed",
      "box-shadow": "none",
      "font-weight": "bold"
    });
  } else {
    button.css({
      "background-color": "#4267B2",
      "color": "white",
      "font-weight": "bold",
      "padding": "10px 20px",
      "border-radius": "8px",
      "border": "none",
      "cursor": "pointer",
      "box-shadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
      "transition": "background-color 0.3s ease"
    });
  }
}

frappe.dom.set_style(`
  @keyframes pulse {
    0% {
      box-shadow: 0 0 5px rgba(255, 204, 0, 0.4);
    }
    50% {
      box-shadow: 0 0 15px rgba(255, 204, 0, 0.8);
    }
    100% {
      box-shadow: 0 0 5px rgba(255, 204, 0, 0.4);
    }
  }
`);
