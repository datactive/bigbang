"""
This submodule is responsible for making data about the classification of
email domains available in Python memory.

The data is stored in a CSV file that is provided with the BigBang repository.

This file was generated using a script that is provided for the library for reproducibility.
The script can be found in ``Create Domain-Category Data.ipynb``
"""

import os
import pandas as pd

DOMAIN_DATA_DIR = os.path.dirname(os.path.abspath(__file__))

DOMAIN_DATA_FILENAME = "domain_categories.csv"


def load_data():
    """
    Returns a datafarme with email domains labeled by category.

    Categories include: generic, personal, company, academic, sdo

    Returns
    -------
    data: pandas.DataFrame
    """
    domain_data_path = os.path.join(DOMAIN_DATA_DIR, DOMAIN_DATA_FILENAME)
    return pd.read_csv(domain_data_path, index_col="domain")
