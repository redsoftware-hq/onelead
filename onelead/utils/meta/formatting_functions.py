import re
from datetime import datetime
from frappe.utils import now
import phonenumbers


def format_phone_number(phone_number, default_region="IN"):
    """
    Format phone numbers to 'country code - local number' format.
    
    Args:
        phone_number (str): The raw phone number string.
        default_region (str): Default region code if the country code is missing.
        
    Returns:
        str: Formatted phone number with 'country code - local number'.
    """
    # Preserve the leading `+` if present, but remove everything else
    phone_number = phone_number.strip()  # Remove surrounding whitespace
    if phone_number.startswith("+"):
        cleaned_number = re.sub(r'[^\d+]', '', phone_number)  # Remove everything except digits & `+`
    else:
        cleaned_number = re.sub(r'\D', '', phone_number)  # Remove all non-digit characters

    try:
        # If number starts with '+', parse as an international number
        if cleaned_number.startswith('+'):
            parsed_number = phonenumbers.parse(cleaned_number, None)
        else:
            parsed_number = phonenumbers.parse(cleaned_number, default_region)  # Assume local number

        # Check if the number is valid
        if not phonenumbers.is_possible_number(parsed_number):
            return "Invalid number"

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