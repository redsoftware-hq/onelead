frappe.query_reports["Leads Chart"] = {
    filters: [
        {
            fieldname: "date_filter",
            label: "Date Filter",
            fieldtype: "Select",
            options: ["Monthly", "Yearly"],
            default: "Monthly",
            reqd: 1,
            change: function () {
                frappe.query_report.refresh();
            },
        },
    ],
};
