import frappe
from collections import defaultdict

@frappe.whitelist()
def get(chart_name=None, chart=None, no_cache=None, filters=None, from_date=None, to_date=None, timespan=None, time_interval=None, heatmap_year=None):
    filters = frappe.parse_json(filters) if filters else {}
    status_filter = filters.get("processing_status") or "Processed"
    limit = filters.get("no_of_ads") or 15
    # limit = 15  # Top 15 ads

    # Join Meta Webhook Lead Logs with Ads to get ad_name
    data = frappe.db.sql("""
        SELECT 
            a.ads_name AS ad_label,
            COUNT(*) as total
        FROM `tabMeta Webhook Lead Logs` l
        JOIN `tabMeta Ads` a ON a.name = l.ads
        WHERE l.processing_status = %s
        GROUP BY a.ads_name
        ORDER BY total DESC
        LIMIT %s
    """, (status_filter, limit), as_dict=True)

    labels = [row["ad_label"] for row in data]
    values = [row["total"] for row in data]

    return {
        "labels": labels,
        "datasets": [
            {
                "name": "Lead Count",
                "values": values
            }
        ],
        "type": "bar",
        "colors": ["#36A2EB"],
        "barOptions": {
            "horizontal": True,
            "stacked": False
        }
    }
