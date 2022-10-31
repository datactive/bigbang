<div align="center">
  <a href="https://datactive.github.io/bigbang/">
    <img src="https://github.com/datactive/bigbang/blob/gh-pages/images/bigbang-logo-dark.png?raw=true" align="center" width="200">
  </a>
  <br>
  <br>
</div>

# BigBang

BigBang is a toolkit for studying communications data from collaborative
projects. It currently supports analyzing mailing lists from Sourceforge,
Mailman, ListServ (version 16.5 and 17), Pipermail (version 0.09), Hypermail (version 2.4.0) or [.mbox][mbox] files.

Complete documentation for BigBang can be found on [ReadTheDocs](https://bigbang-py.readthedocs.io/en/latest/).

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

This video tutorial shows how to install BigBang.
[![BigBang Video Tutorial](http://img.youtube.com/vi/JWimku8JVqE/0.jpg)](http://www.youtube.com/watch?v=JWimku8JVqE "BigBang Tutorial")


## Usage

There are serveral Jupyter notebooks in the `examples/` directory of this
repository. To open them and begin exploring, run the following commands in the root directory of this repository:

```bash
source activate bigbang
ipython notebook examples/
```

BigBang contains scripts that make it easy to collect data from a variety of sources.
For example, to collect data from an open mailing list archive hosted by Mailman, use:

```bash
python3 bin/collect_mail.py -u http://mail.python.org/pipermail/scipy-dev/
```

You can also give this command a file with several urls, one per line. One of these is provided in the `examples/` directory.

```bash
python3 bin/collect_mail.py -f examples/urls.txt
```

Once the data has been collected, BigBang has functions to support analysis.

You can read more about data source supported by BigBang in the [documentation](https://bigbang-py.readthedocs.io/).

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

## Publications

These academic publications use BigBang as part of their methods:

- Becker, Christoph., ten Oever, Niels, and Riccardo Nanni. 2022 “The standardisation of lawful interception technologies in the 3GPP: interrogating 5G and surveillance amid US-China competition“, TPRC2022, Washington DC https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4167105
- Benthall, Sebastian. 2015. “Testing Generative Models of Online Collaboration with BigBang.” In , 182–89. https://conference.scipy.org/proceedings/scipy2015/sebastian_benthall.html.
- Doty, Nick. 2015. “Reviewing for Privacy in Internet and Web Standard-Setting.” In Security and Privacy Workshops (SPW), 2015 IEEE, 185–192. IEEE. https://ieeexplore.ieee.org/document/7163224/
- Milan, Stefania, and Niels ten Oever. 2017. “Coding and Encoding Rights in Internet Infrastructure.” Internet Policy Review 6 (1)
- ten Oever, Niels. 2018. “Productive Contestation, Civil Society, and Global Governance: Human Rights as a Boundary Object in ICANN.” Policy & Internet, June. https://doi.org/10.1002/poi3.172.
- Nanni, Riccardo. “Digital Sovereignty and Internet Standards: Normative Implications of Public-Private Relations among Chinese Stakeholders in the Internet Engineering Task Force.” Information, Communication & Society 0, no. 0 (October 1, 2022): 1–21. https://doi.org/10.1080/1369118X.2022.2129270.
- ten Oever, Niels. 2021. “‘This Is Not How We Imagined It’ -  Technological Affordances, Economic Drivers and the Internet Architecture Imaginary.” New Media & Society. https://journals.sagepub.com/doi/full/10.1177/1461444820929320
- ten Oever, N., Milan, S., & Beraldo, D. (2020). Studying Discourse in Internet Governance through Mailing-list Analysis. In D. L. Cogburn, L. DeNardis, N. S. Levinson, & F. Musiani (Eds.), Research Methods in Internet Governance. Cambridge, MA: MIT Press. https://direct.mit.edu/books/oa-monograph/4936/chapter/625914/Studying-Discourse-in-Internet-Governance-through


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
