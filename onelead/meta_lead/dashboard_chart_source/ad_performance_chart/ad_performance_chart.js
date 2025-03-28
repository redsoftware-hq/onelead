frappe.dashboards.chart_sources["Ad Performance Chart"] = {
  method: "onelead.meta_lead.dashboard_chart_source.ad_performance_chart.ad_performance_chart.get",
  filters: [
    {
      fieldname: "processing_status",
      label: __("Processing Status"),
      fieldtype: "Select",
      options: "\nProcessed\nError\nUnconfigured",
      default: "Processed"
    },
    {
      fieldname: "no_of_ads",
      label: __("No of Ads"),
      fieldtype: "Int",
      default: 15
    }
  ]
}
