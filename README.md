# BigBang

BigBang is a toolkit for studying communications data from collaborative
projects. It currently supports analyzing mailing lists from Sourceforge,
Mailman, or [.mbox][mbox] files.

[mbox]: http://tools.ietf.org/html/rfc4155

## Installation

BigBang depends on several scientific computing packages that you must first install on your system, which include:

* [numpy](http://docs.scipy.org/doc/numpy/user/install.html)
* [matplotlib](http://matplotlib.org/users/installing.html)
* [graphviz](http://www.graphviz.org/)


You can use the [Anaconda](http://tools.ietf.org/html/rfc4155) distribution to
install `numpy` and `matplotlib` on almost any platform. This will also install
the `conda` package management system, which you can use to complete
installation. **Note** that Anaconda does not include Graphviz, so you will
have to install that separately.

If you choose not to use Anaconda, you will have to install each of the
above-mentioned packages for your platform. If you're using OS X [these instructions][osx] may be helpful.

[osx]: http://www.lowindata.com/2013/installing-scientific-python-on-mac-os-x/

Once these dependencies are installed, you can install BigBang
using either `conda` or `pip`.

### conda installation

Run the following commands:

    git clone https://github.com/sbenthall/bigbang.git
    conda create -n bigbang python
    cd bigbang
    bash conda-setup.sh

### pip installation

Run the following commands:

    git clone https://github.com/sbenthall/bigbang.git
    # optionally create a new virtualenv here
    pip install -r requirements.txt
    python setup.py develop

## Usage

There are serveral IPython notebooks in the `examples/` directory of this
repository. To open them and begin exploring, run the following commands in the
root directory of this repository:

    source activate bigbang
    ipython notebook examples/

### Collecting from Mailman

BigBang comes with a script for collecting files from public Mailman web
archives. An example of this is the
[scipy-dev](http://mail.scipy.org/pipermail/scipy-dev/) mailing list page. To
collect the archives of the scipy-dev mailing list, run the following command
from the root directory of this repository:

    python bin/collect_mail.py -u http://mail.scipy.org/pipermail/scipy-dev/

You can also give this command a file with several urls, one per line. One of these is provided in the `examples/` directory.

    python bin/collect_mail.py -f examples/urls.txt

Once the data has been collected, BigBang has functions to support analysis.

## License

GPLv2, see LICENSE for its text.
