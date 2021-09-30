<div align="center">
  <a href="https://datactive.github.io/bigbang/">
    <img src="https://github.com/datactive/bigbang/blob/gh-pages/images/bigbang-logo-dark.png?raw=true" align="center" width="500">
  </a>
  <br>
  <br>
</div>

# BigBang

BigBang is a toolkit for studying communications data from collaborative
projects. It currently supports analyzing mailing lists from Sourceforge,
Mailman, or [.mbox][mbox] files.

[mbox]: http://tools.ietf.org/html/rfc4155

[![DOI](https://img.shields.io/badge/DIO-10.25080%2FMajora--7b98e3ed--01b-blue)](http://conference.scipy.org/proceedings/scipy2015/sebastian_benthall.html)
[![codecov](https://codecov.io/gh/datactive/bigbang/branch/main/graph/badge.svg?token=Nhyl6g4ZIO)](https://codecov.io/gh/datactive/bigbang)
[![Gitter](https://badges.gitter.im/datactive/bigbang.svg)](https://gitter.im/datactive/bigbang?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)

## Installation*

You can use [Anaconda](https://www.anaconda.com/). This will also install
the `conda` package management system, which you can use to complete
installation.

[Install Anaconda](https://www.anaconda.com/download/), with Python version
3.*.

If you choose not to use Anaconda, you may run into issues with versioning in
Python. Add the Conda installation directory to your path during installation.

You also need need to have Git and Pip (for Python3) installed.

Run the following commands:

```bash

git clone https://github.com/datactive/bigbang.git
cd bigbang
bash conda-setup.sh
python3 setup.py develop --user
```

## Usage

There are serveral Jupyter notebooks in the `examples/` directory of this
repository. To open them and begin exploring, run the following commands in the root directory of this repository:

```bash
source activate bigbang
ipython notebook examples/
```

### Collecting mail archives

BigBang comes with a script for collecting files from public Mailman web
archives. An example of this is the
[scipy-dev](http://mail.python.org/pipermail/scipy-dev/) mailing list page. To
collect the archives of the scipy-dev mailing list, run the following command
from the root directory of this repository:

```bash
python3 bin/collect_mail.py -u http://mail.python.org/pipermail/scipy-dev/
```

You can also give this command a file with several urls, one per line. One of these is provided in the `examples/` directory.

```bash
python3 bin/collect_mail.py -f examples/urls.txt
```

Once the data has been collected, BigBang has functions to support analysis.

### Collecting IETF draft metadata

BigBang can also be used to analyze data from IETF drafts.

It does this using the Glasgow IPL group's `ietfdata` [tool](https://github.com/glasgow-ipl/ietfdata).

The script takes an argument, the working group acronym

```bash
python3 bin/collect_draft_metadata.py -w httpbis
```

### Git

BigBang can also be used to analyze data from Git repositories.

Documentation on this feature can be found [here](https://github.com/datactive/bigbang/blob/master/git-readme.md).

## Development

### Unit tests

To run the automated unit tests, use: `pytest tests/unit`.

Our current goal is code coverage of **60%**. Add new unit tests within `tests/unit`. Unit tests run quickly, without relying on network requests.

### Documentation

Docstrings are preferred, so that auto-generated web-based documentation will be possible ([#412](https://github.com/datactive/bigbang/issues/412)). You can follow the [Google style guide for docstrings](https://github.com/google/styleguide/blob/gh-pages/pyguide.md#38-comments-and-docstrings).

### Formatting

Run `pre-commit install` to get automated usage of `black`, `flake8` and `isort` to all Python code files for consistent formatting across developers. We try to follow the [PEP8 style guide](https://pep8.org/).

## Community

If you are interested in participating in BigBang development or would like support from the core development team, please subscribe to the [bigbang-dev mailing list](https://lists.ghserv.net/mailman/listinfo/bigbang-dev) and let us know your suggestions, questions, requests and comments. A [development chatroom](https://gitter.im/datactive/bigbang) is also available.

In the interest of fostering an open and welcoming environment, we as contributors and maintainers [pledge to make participation in our project and our community a harassment-free experience for everyone](CODE_OF_CONDUCT.md).

## Troubleshooting

If the installation described above does not work, you can try to run the installation with Pip:

```bash
git clone https://github.com/datactive/bigbang.git
# optionally create a new virtualenv here
pip3 install -r requirements.txt
python3 setup.py develop --user
```
If you have problems installing, you might want to have a look at the video tutorial below (clicking on the image will take you to YouTube).

[![BigBang Video Tutorial](http://img.youtube.com/vi/JWimku8JVqE/0.jpg)](http://www.youtube.com/watch?v=JWimku8JVqE "BigBang Tutorial")

## Data Access Permit Application
The mailing-list archives are large and time consuming to scrape from the web. That is why we keep a complete and up-to-date copy of it in .mbox format that can easily be converted into other data structures to make its analysis as easy as possible. If you would like to obtain access to these archives, we would ask you send us your filled in [data access permit application](https://github.com/datactive/bigbang/blob/master/data_access_permit_application.md) to [bigbang-dev mailing list](https://lists.ghserv.net/mailman/listinfo/bigbang-dev).

## License

MIT, see [LICENSE](LICENSE) for its text. This license may be changed at any time according to the principles of the project [Governance](https://github.com/datactive/bigbang/wiki/Governance).

## Acknowledgements 

This project is funded by:

<div align="center">
  <a href="https://www.bmbf.de/bmbf/de/home/home_node.html">
    <img src="https://github.com/datactive/bigbang/blob/gh-pages/images/logo_bmbf.png?raw=true" align="center">
  </a>
  <a href="https://prototypefund.de/">
    <img src="https://github.com/datactive/bigbang/blob/gh-pages/images/logo_prototypefund.png?raw=true" align="center">
  </a>
  <br>
  <br>
</div>
