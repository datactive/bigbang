import os
import pandas as pd

DOMAIN_DATA_DIR = os.path.dirname(os.path.abspath(__file__))

DOMAIN_DATA_FILENAME = "domain_categories.csv"


def load_data():
    """
    Returns a datafarme with email domains labeled by category.

    Categories include: generic, personal, company, academic, sdo
    """
    domain_data_path = os.path.join(DOMAIN_DATA_DIR, DOMAIN_DATA_FILENAME)
    return pd.read_csv(domain_data_path, index_col="domain")
