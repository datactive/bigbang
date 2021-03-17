conda env create --file environment.yml
source activate bigbang
pip install --upgrade-strategy only-if-needed -r requirements.txt
