import sys
import warnings

from snakefood import gendeps

warnings.simplefilter("ignore", UserWarning)
sys.stdout = open("dependencies.txt", "w")


def main():
    gendeps.gendeps()


if __name__ == "__main__":
    main()
