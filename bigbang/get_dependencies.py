import warnings
warnings.simplefilter("ignore", UserWarning)
import sys
from snakefood import gendeps
sys.stdout = open("dependencies.txt", "w")

def main():
	gendeps.gendeps()

if __name__ == "__main__": main()
