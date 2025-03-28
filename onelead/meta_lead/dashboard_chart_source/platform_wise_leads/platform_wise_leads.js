frappe.dashboards.chart_sources["Platform wise Leads"] = {
  method: "onelead.meta_lead.dashboard_chart_source.platform_wise_leads.platform_wise_leads.get",
  filters: [
    {
      fieldname: "processing_status",
      label: __("Processing Status"),
      fieldtype: "Select",
      options: "\nProcessed\nError\nPending\nUnconfigured\nDisabled",
      default: "Processed"
    }
  ]
}
