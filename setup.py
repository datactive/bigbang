import sys
import subprocess
from setuptools import setup
from setuptools.command.develop import develop


class PreCommitCommand(develop):
    """
    Install pre-commit hook after all required packages are installed.
    """

    def run(self):
        try:
            cmd = (sys.executable, "-m", "pre_commit", "install")
            if not subprocess.call(cmd):
                return
        except Exception as e:
            raise SystemExit(f'Unable to run "pre-commit install" because {e}')
        develop.run(self)


# required dependencies
install_requires = [
    "beautifulsoup4>=4.9.3",
    "chardet>=4.0.0",
    "common>=0.1.2",
    "enlighten>=1.7.2",
    "gender-detector",
    "GitPython",
    "html2text>=2020.1.16",
    "ietfdata>=0.4.0",
    "ipython>=7.22.0",
    "jinja2>=2.11.3",
    "jupyter>=1.0.0",
    "jsonschema>=3.2.0",
    "matplotlib>=3.4.1",
    "networkx>=2.5.1",
    "nltk>=3.6.2",
    "numpy>=1.20.2",
    "pandas>=1.2.3",
    "powerlaw>=1.4.6",
    "python-dateutil>=2.8.1",
    "python-Levenshtein>=0.12.2",
    "pytz>=2021.1",
    "pyyaml>=5.4.1",
    "pyzmq>=22.0.3",
    "requests>=2.25.1",
    "seaborn",
    "tornado>=6.1",
    "tqdm>=4.60.0",
    "validator_collection>=1.5.0",
    "python-docx>=0.8",
]
# test dependencies
test_requires = ["pytest>=6.2.3", "coverage>=5.5", "testfixtures>=6.17.1"]
# development dependencies
dev_requires = [
    "black>=20.8b1",
    "isort>=5.7.0",
    "pre-commit>=2.13.0",
]

config = {
    "name": "BigBang",
    "version": "0.4.1",
    "description": "BigBang is a toolkit for studying communications data from collaborative projects. It currently supports analyzing mailing lists from Sourceforge, Mailman, ListServ, or .mbox files.",
    "author": "BigBang Team",
    "author_email": "bigbang-dev@data-activism.net",
    "packages": ["bigbang"],
    "install_requires": install_requires,
    "extras_require": {
        "test": test_requires,
        "dev": test_requires + dev_requires,
    },
    "cmdclass": {"develop": PreCommitCommand},
}

setup(**config)
