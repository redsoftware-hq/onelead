import frappe
import re
from datetime import datetime
from frappe.utils import now
import phonenumbers

# Define a global dictionary to store function names dynamically
FORMATTING_FUNCTIONS = {}

@frappe.whitelist()
def get_function_names():
    """Return a list of available function names for the Select field."""
    return list(FORMATTING_FUNCTIONS.keys())

def register_function(name):
    """Decorator to register a function in the global FORMATTING_FUNCTIONS dictionary."""
    def wrapper(func):
        FORMATTING_FUNCTIONS[name] = func
        return func
    return wrapper

@register_function("format_phone_number")
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
            national_number = str(parsed_number.national_number)
            if cleaned_number.startswith(str(parsed_number.country_code)):  # Avoid adding duplicate country code
                cleaned_number = national_number
                parsed_number = phonenumbers.parse(cleaned_number, default_region)

        # Check if the number is valid
        if not phonenumbers.is_possible_number(parsed_number):
            return "Invalid number"

        # Get the country code and national number
        country_code = parsed_number.country_code
        national_number = parsed_number.national_number

        return f"+{country_code}-{national_number}"

    except phonenumbers.NumberParseException:
        return "Invalid number"

@register_function("calculate_age")
def calculate_age(dob_str, dob_format="%Y-%m-%d"):
    """Calculate age given a date of birth string."""
    try:
        dob = datetime.strptime(dob_str, dob_format)
        today = datetime.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except ValueError:
        return None 

@register_function("extract_country_from_address")
def extract_country_from_address(address):
    """Extract country from an address string if the country is the last element."""
    parts = address.strip().split(',')
    return parts[-1].strip() if len(parts) > 1 else None

@register_function("add_prefix")
def add_prefix(value, prefix=""):
    """Add a prefix to a value if it's not empty."""
    return f"{prefix}{value}" if value else value

@register_function("capitalize_name")
def capitalize_name(name):
    """Capitalize each part of a name."""
    return ' '.join([word.capitalize() for word in name.split()])

@register_function("current_date")
def current_date():
    """add current date"""
    return now()

# Dictionary to map function names to actual functions
# formatting_functions = {
#     "format_phone_number": format_phone_number,
# }