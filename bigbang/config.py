import yaml
import os

bigbang_path = os.path.dirname(os.path.realpath(__file__))
base_loc = os.path.abspath(
    os.path.join(bigbang_path, os.pardir)
)  # parent directory of config directory
config_filepath = os.path.join(base_loc, "bigbang", "config.yml")
stream = open(config_filepath, "r")
dictionary = yaml.safe_load(stream)


class Config(object):
    def __init__(self, conf):
        self.CONFIG = conf

    def __getattr__(self, query):
        if query in self.CONFIG:
            ans = self.CONFIG[query]
            if "path" in query:
                ans = os.path.join(os.getcwd(), ans)
            return ans
        else:
            return None


CONFIG = Config(dictionary)
