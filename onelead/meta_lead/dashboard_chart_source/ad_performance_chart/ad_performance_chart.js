frappe.dashboards.chart_sources["Ad Performance Chart"] = {
  method: "onelead.meta_lead.dashboard_chart_source.ad_performance_chart.ad_performance_chart.get",
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
