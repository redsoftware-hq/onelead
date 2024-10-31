import re
from datetime import datetime
from frappe.utils import now
import phonenumbers
    
def format_phone_number(phone_number, code="+1"):
    """
    Format phone numbers to 'country code - local number' format.
    Args:
        phone_number (str): The raw phone number string.
        default_region (str): Default region code if the country code is missing.
    Returns:
        str: Formatted phone number with 'country code - local number'.
    """
    # Clean default_code by removing non-numeric characters
    code = re.sub(r'[^\d]', '', code)

    # Remove all non-numeric characters except the plus sign in phone_number
    cleaned_number = re.sub(r'[^\d+]', '', phone_number)
    
    # If the number starts without '+', assume it's missing the country code
    if not cleaned_number.startswith('+'):
        cleaned_number = f"+{code}{cleaned_number}"
    
    try:
        # Parse the phone number
        parsed_number = phonenumbers.parse(cleaned_number)
        
        # Get the country code and national number
        country_code = parsed_number.country_code
        national_number = parsed_number.national_number
        
        return f"+{country_code}-{national_number}"
    except phonenumbers.NumberParseException:
        return "Invalid number"

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