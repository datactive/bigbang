import logging
import os
import subprocess
from pathlib import Path
from sys import argv

project_directory = Path(os.path.abspath(__file__)).parent.parent

working_directory = Path(os.getcwd())

working_directory_parent = working_directory.parent


def find_default(name: str, look_in_package=True) -> Path:
    """
    Get a default path when no command line argument is passed.
    - First attempt to find the folder in the current working directory.
    - If it is not found there then try the directory in which BigBang lives.
    - Finally, try the directory above the current working directory. This
        is for the build pipeline.

    This means that tests will find the configuration regardless of whether
    they are run together or individually.

    Parameters
    ----------
    name
        The name of some folder

    Returns
    -------
    The full path to that directory
    """
    directories_to_look = [working_directory, working_directory_parent]
    if look_in_package:
        directories_to_look.append(project_directory)
        directories_to_look.append(project_directory.parent)
    for directory in directories_to_look:
        path = directory / name
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"Could not find a default path for {name}")


def path_for_name(name: str, look_in_package=True) -> Path:
    """
    Get a path input using a flag when the program is run.

    e.g. --archives indicates where the archives folder is and defaults
        to bigbang/archives

    Parameters
    ----------
    name
        A string such as "archives" which corresponds to the flag --archives

    Returns
    -------
    A path
    """
    flag = f"--{name}"
    try:
        path = Path(argv[argv.index(flag) + 1])
        if not path.exists():
            raise FileNotFoundError(f"No such folder {path}")
    except (IndexError, ValueError):
        path = find_default(name, look_in_package=look_in_package)

    return path


try:
    archives_path = path_for_name("archives", look_in_package=True)
except FileNotFoundError:
    answer = input(
        "Couldn't find any 'archives' folder"
    )

configs_path = path_for_name("config")
