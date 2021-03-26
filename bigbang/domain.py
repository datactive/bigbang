import math
import re

import pandas as pd

email_regex = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
domain_regex = r"[@]([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$"


def extract_email(from_field):
    """
    Returns an email address from a string.
    """
    match = re.search(email_regex, from_field)

    if match is not None:
        return match[0].lower()

    else:
        return None


def extract_domain(from_field):
    """
    Returns the domain of an email address from a string.
    """
    match = re.search(email_regex, from_field)

    if match is not None:
        return re.search(domain_regex, match[0])[1]

    else:
        return None
