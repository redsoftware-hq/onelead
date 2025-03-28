import frappe
from frappe.utils import getdate, nowdate, add_days, add_months, add_years
from collections import defaultdict
import datetime
import calendar

@frappe.whitelist()
def get(chart_name=None, chart=None, no_cache=None, filters=None,
        from_date=None, to_date=None, timespan=None, time_interval=None, heatmap_year=None):
    
    filters = frappe.parse_json(filters) if filters else {}
    status_filter = filters.get("processing_status") or "Processed"

    today = getdate(nowdate())
    if not from_date:
      if timespan == "Last Week":
          from_date = add_days(today, -7)
      elif timespan == "Last Month":
          from_date = add_months(today, -1)
      elif timespan == "Last Quarter":
          from_date = add_months(today, -3)
      elif timespan == "Last Year":
          from_date = add_years(today, -1)
      else:
          from_date = add_months(today, -3)  # default to 6 weeks

    from_date = getdate(from_date)
    to_date = getdate(to_date or today)

    # Grouping format based on time interval
    if time_interval == "Daily":
        sql_period = "DATE(created_time)"
    elif time_interval == "Weekly":
        sql_period = "YEARWEEK(created_time, 3)"
    elif time_interval == "Monthly":
        sql_period = "DATE_FORMAT(creation, '%%Y-%%m')"
    elif time_interval == "Quarterly":
        sql_period = "CONCAT(YEAR(created_time), '-Q', QUARTER(created_time))"
    elif time_interval == "Yearly":
        sql_period = "YEAR(created_time)"
    else:
        sql_period = "YEARWEEK(created_time, 3)"  # default to weekly

    doc_type = "Meta Webhook Lead Logs"
    # Fetch weekly lead count grouped by platform
    raw_data = frappe.db.sql(f"""
        SELECT 
            {sql_period} AS period,
            platform,
            COUNT(*) as count
        FROM `tab{doc_type}`
        WHERE processing_status = %s
          AND created_time BETWEEN %s AND %s
        GROUP BY period, platform
        ORDER BY period ASC
    """, (status_filter, from_date, to_date), as_dict=True)

    period_map = defaultdict(lambda: {"Instagram": 0, "Facebook": 0})
    label_map = {}

    print(filters)
    print(from_date, to_date)
    print(raw_data)

    for row in raw_data:
        period = row["period"]
        platform = row["platform"]
        count = row["count"]
        label = str(period)

        # if time_interval == "Weekly":
        #     # Convert "202452" -> readable range
        #     year = int(str(period)[:4])
        #     week = int(str(period)[4:])
        #     start_of_week = datetime.date.fromisocalendar(year, week, 1)
        #     end_of_week = start_of_week + datetime.timedelta(days=6)
        #     label = f"Week {week}\n{start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d')}"
        if time_interval == "Weekly" and isinstance(period, int):
            year = int(str(period)[:4])
            week = int(str(period)[4:])
            try:
                start_of_week = datetime.date.fromisocalendar(year, week, 1)
                end_of_week = start_of_week + datetime.timedelta(days=6)
                label = f"Week {week}\n{start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d')}"
            except Exception:
                pass  # fallback to numeric label

        elif time_interval == "Daily":
            try:
                label = getdate(period).strftime("%b %d")
            except Exception:
                pass

        elif time_interval == "Monthly":
            try:
                label = datetime.datetime.strptime(period, "%Y-%m").strftime("%b %Y")
            except Exception:
                pass

        elif time_interval == "Quarterly":
            label = str(period)  # e.g. "2024-Q4"

        elif time_interval == "Yearly":
            label = str(period) 

        period_map[label][platform] = count
        label_map[period] = label

    labels = sorted(period_map.keys())
    instagram_data = [period_map[l]["Instagram"] for l in labels]
    facebook_data = [period_map[l]["Facebook"] for l in labels]
    all_data = [period_map[l]["Instagram"] + period_map[l]["Facebook"] for l in labels]

    return {
        "labels": labels,
        "datasets": [
            {"name": "Instagram", "values": instagram_data, "chartType": 'bar' },
            {"name": "Facebook", "values": facebook_data, "chartType": 'bar'},
            {"name": "Total", "values": all_data, "chartType": 'bar', "isVisible": 0},
        ],
        "type": "bar",
        
        "colors": ['#ffeb3b','#ee82ee'],
        "valuesOverPoints": 0,
        "barOptions": {"stacked": 1, "spaceRatio": 0.5 }
    }
