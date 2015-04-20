import yaml
import os
base_loc = os.path.dirname(os.path.realpath(__file__))
last_index = repoLocation.rfind("/")
base_loc = base_loc[0:last_index] + "/"

stream = open("config.yml", "r")
docs = yaml.load_all(stream)
for doc in docs:
    for k,v in doc.items():
        print k, "->", v
    print "\n",