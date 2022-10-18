import bigbang.analysis.utils as utils

import unittest
import yaml as yaml

import os

TEST_FILENAME = os.path.join(
    os.path.dirname(__file__), "../data/address_header_test_file.yaml"
)


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


"""
class TestExtractEmail(unittest.TestCase):
    def test_extract_email(self):
        with open(TEST_FILENAME) as file:
            data = file.read()

            dct = yaml.safe_load(data)


class TestExtractDomain(unittest.TestCase):
    def test_extract_domain(self):
        with open(TEST_FILENAME) as file:
            data = file.read()

            dct = yaml.safe_load(data)

            for header in dct:
                import pdb; pdb.set_trace()
                self.assertEqual(utils.extract_domain(header), dct[header]['domain'].lower())
"""
