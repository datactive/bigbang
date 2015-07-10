try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description': 'Analysis of Mailman archives',
    'author': 'Sebastian Benthall',
    'url': 'URL to get it at.',
    'download_url': 'Where to download it.',
    'author_email': 'sb@ischool.berkeley.edu',
    'version': '0.1',
    'install_requires': [
        'beautifulsoup4',
        'chardet',
        'coverage',
        'html2text',
        'ipython',
        'jinja2',
        'jsonschema',
        'matplotlib',
        'networkx',
        'nose',
        'numpy',
        'pandas',
        'python-dateutil',
        'python-Levenshtein',
        'pytz',
        'pyzmq',
        'snakefood',
        'tornado',
        'requests',
        'pyyaml',
        'common',
        'powerlaw'],
    'packages': ['bigbang'],
    'scripts': [],
    'name': 'BigBang'}

setup(**config)
