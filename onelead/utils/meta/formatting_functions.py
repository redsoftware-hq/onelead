import re
from datetime import datetime
from frappe.utils import now

def format_phone_number(phone_number, code="+1"):
    """Format phone numbers to international format."""
    # Remove all non-numeric characters except the plus at the start
    cleaned_number = re.sub(r'[^\d+]', '', phone_number)
    
    # If the number starts without '+', assume it's missing the country code
    if not cleaned_number.startswith('+'):
        cleaned_number = f"{code}{cleaned_number}"
    
    # Format with spaces for readability
    # Example: +1234567890 -> +1 234 567 890
    formatted_number = re.sub(r"(\+?\d{1,3})(\d{3})(\d{3})(\d+)", r"\1 \2 \3 \4", cleaned_number)
    
    return formatted_number

def calculate_age(dob_str, dob_format="%Y-%m-%d"):
    """Calculate age given a date of birth string."""
    try:
        dob = datetime.strptime(dob_str, dob_format)
        today = datetime.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except ValueError:
        return None 

def extract_country_from_address(address):
    """Extract country from an address string if the country is the last element."""
    parts = address.strip().split(',')
    return parts[-1].strip() if len(parts) > 1 else None

def add_prefix(value, prefix=""):
    """Add a prefix to a value if it's not empty."""
    return f"{prefix}{value}" if value else value

def capitalize_name(name):
    """Capitalize each part of a name."""
    return ' '.join([word.capitalize() for word in name.split()])

def now(current_value):
    """add current date"""
    return now()
# Dictionary to map function names to actual functions
# formatting_functions = {
#     "format_phone_number": format_phone_number,
# }