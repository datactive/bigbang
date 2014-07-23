bigbang
=======

Bigbang is a toolkit for studying communications data from collaborative projects.

The focus of the early milestones will be on mailing list or listserve analysis,
  with a focus on Mailman and Sourceforge mail archives, as well as .mbox files.

Installation
------------

Big Bang uses a lot of SciPy packages that use native (e.g. C) code.
These need to be installed separately.

* [numpy](http://docs.scipy.org/doc/numpy/user/install.html)
* [matplotlib](http://matplotlib.org/users/installing.html)
* [graphviz](http://www.graphviz.org/)

You might try to [Anaconda](https://store.continuum.io/cshop/anaconda/) Python distribution, which comes with these and other packages installed easily.

1. Clone this repo.

2. (Optional) Make a new virtualenv.

3. `cd` into the directory of the cloned repo and run

    `python setup.py develop `
 
