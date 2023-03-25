Installation
**************

conda
=======

You can use `Anaconda <https://www.anaconda.com/>`_. This will also install
the `conda` package management system, which you can use to complete
installation.

`Install Anaconda <https://www.anaconda.com/download/>`_, with Python version
3.*.

If you choose not to use Anaconda, you may run into issues with versioning in
Python. Add the Conda installation directory to your path during installation.

You also need need to have Git and Pip (for Python3) installed.

Run the following commands:

.. code-block:: console
    
    conda create -n bigbang 
    git clone https://github.com/datactive/bigbang.git
    cd bigbang
    pip install .[dev]

pip
=======

.. code-block:: console

    git clone https://github.com/datactive/bigbang.git
    # optionally create a new virtualenv here
    pip3 install -r requirements.txt
    python3 setup.py develop --user
    

Video Tutorial
=================

If you have problems installing, you might want to have a look at the video tutorial 
below (clicking on the image will take you to YouTube).

`BigBang Video Tutorial <http://www.youtube.com/watch?v=JWimku8JVqE>`_
