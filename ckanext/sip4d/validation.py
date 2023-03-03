from dateutil.parser import parse
import ckan.plugins.toolkit as tk


def date_str_validator(value, context=None):
    if value is None or len(value) == 0:
        return value
    try:
        valid_date = parse(value)
        DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
        return valid_date.strftime(DATETIME_FORMAT)
    except (TypeError, ValueError):
        raise tk.Invalid("Invalid date")


def str_date_validator(value, context=None):
    if value is None or len(value) == 0:
        return value
    try:
        valid_date = parse(value)
    except (TypeError, ValueError):
        raise tk.Invalid("Invalid datetime")
    return valid_date
