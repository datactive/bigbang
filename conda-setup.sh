conda install -n bigbang -c https://conda.binstar.org/asmeurer --file conda-requirements.txt
source activate bigbang
pip install chardet
pip install html2text
pip install python-Levenshtein
pip install common
pip install git+https://github.com/gitpython-developers/GitPython.git
pip install -e .
