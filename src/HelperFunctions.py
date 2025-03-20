import os

"""
Someday it will be best to move all global functions into here.
"""


def list_files_in_directory(directory_path):
    try:
        files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]
        return files
    except FileNotFoundError:
        print("Fail")
