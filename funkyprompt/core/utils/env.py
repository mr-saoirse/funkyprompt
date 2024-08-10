import os
from pathlib import Path
from importlib import import_module

POSTGRES_DB = "postgres"
POSTGRES_SERVER = "localhost"
POSTGRES_PORT = 5432
POSTGRES_PASSWORD = "password"
POSTGRES_USER = "sirsh"
POSTGRES_CONNECTION_STRING = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
AGE_GRAPH = "funkybrain"
STORE_ROOT = os.environ.get('FUNKY_HOME',f"{Path.home()}/.funkyprompt")

def get_repo_root():
    """the root directory of the project"""
    path = os.environ.get("FUNKY_REPO_HOME")
    if not path:
        one = import_module("funkyprompt")
        if one.__file__ is not None:
            path = Path(one.__file__).parent.parent
        else:
            path = Path(__file__).parent.parent.parent
    return Path(path)