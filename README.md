# BigBang
=======

BigBang is a toolkit for studying communications data from collaborative projects.

The focus of the early milestones will be on mailing list or listserve analysis,
  with a focus on Mailman and Sourceforge mail archives, as well as .mbox files.

## Installation

BigBang uses a lot of SciPy packages that use native (e.g. C) code.
This complicates installation.

There are two package management systems you can use for installing Python projects.
I recommend using conda for installation. You can also use pip.

### conda installation

The [Anaconda](https://store.continuum.io/cshop/anaconda/) Python distribution which comes with scientific packages pre-installed and the ``conda`` package management system.

1. Clone this repository:

    ``git clone git@github.com:sbenthall/bigbang.git``

2. Make a new conda environment called ``bigbang``

    ``conda create -n bigbang python``

3. Run this script to install the dependencies

    ``cd bigbang``
    
    ``bash conda-setup.sh``
``

You should be good to go.

### pip installation

You're going to have to manually install a bunch of programs if you do it this way. 
You can try following [these instructions](http://www.lowindata.com/2013/installing-scientific-python-on-mac-os-x/) for installing various Scientific Python packages using Homebrew and pip.

These are some of the packages you will need to install. You can discover others ones you will need be seeing where pip chokes.

* [numpy](http://docs.scipy.org/doc/numpy/user/install.html)
* [matplotlib](http://matplotlib.org/users/installing.html)
* [graphviz](http://www.graphviz.org/)

When you think you've got what you need installed, follow these instructions:

1. Clone this repo.

2. (Optional) Make a new virtualenv.

3. Install the remaining dependencies to the virtual environment using pip.

    ``pip install -r requirements.txt``

4. `cd` into the directory of the cloned repo and run

    `python setup.py develop `
 
## Using BigBang

BigBang is presently an environment for scientific exploration of mailing list data.

The best way to learn about how to use BigBang is to look at the I Python notebook examples provided in this repository.
In the home directory of this repository, run:

    source activate bigbang
    ipython notebook examples/

and play around.

## Usage

BigBang supports data collection from public mailing lists and data analysis.

### Collecting from Mailman

BigBang comes with a script for collecting files from public Mailman web archives. And example of this is the [scipy-dev](http://mail.scipy.org/pipermail/scipy-dev/) mailing list page.

From the directory of the this checked out repository, you can collect the archives from a web URL with the following command:

    `python bin/collect_mail.py -u http://mail.scipy.org/pipermail/scipy-dev/`

You can also give this command a file with several urls, one per line. One of these is provided in the `examples/` directory.

    `python bin/collect_mail.py -f examples/urls.txt`

Once the data has been collected, BigBang has functions to support analysis.
