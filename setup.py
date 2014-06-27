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
    'install_requires': ['nose','networkx','pydot','pytz'],
    'packages': ['bigbang'],
    'scripts': [],
    'name': 'BigBang'
}

setup(**config)
