import frappe

def execute(filters=None):
    conditions = "WHERE ad_id IS NOT NULL"
    values = {}

    # Apply Monthly Filter
    if filters and filters.get("date_filter") == "Monthly":
        conditions += " AND MONTH(creation) = MONTH(CURDATE()) AND YEAR(creation) = YEAR(CURDATE())"

    # Apply Yearly Filter
    elif filters and filters.get("date_filter") == "Yearly":
        conditions += " AND YEAR(creation) = YEAR(CURDATE())"

    query = f"""
        SELECT 
            ad_id,
            DATE(creation) AS lead_date,  
            COUNT(name) AS lead_count
        FROM 
            `tabMeta Webhook Lead Logs`
        {conditions}  
        GROUP BY 
            ad_id, lead_date  
        ORDER BY 
            lead_date DESC, lead_count DESC
    """
    
    data = frappe.db.sql(query, values=values, as_dict=True)

    columns = [
        {"label": "Ad ID", "fieldname": "ad_id", "fieldtype": "Data", "width": 200},
        {"label": "Lead Date", "fieldname": "lead_date", "fieldtype": "Date", "width": 150},  
        {"label": "Lead Count", "fieldname": "lead_count", "fieldtype": "Int", "width": 150},
    ]

    return columns, data
