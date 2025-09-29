# contracts.py
import codeon.settings as sts
import os, sys
import codeon.arguments as arguments
from codeon.helpers.dir_context import DirContext
from colorama import Fore, Style


def checks(*args, **kwargs):
    kwargs = clean_kwargs(*args, **kwargs)
    check_missing_kwargs(*args, **kwargs)
    kwargs.update(get_package_data(*args, **kwargs))
    kwargs.update(clean_paths(*args, **kwargs))
    check_env_vars(*args, **kwargs)
    return kwargs

def check_env_vars(*args, **kwargs):
    """
    Some processes like pm2 run the application without environment variables.
    This function checks if the required environment variables are set.
    If not it adds them by loading the .env file.
    """
    if os.environ.get('pg_alias') is None:
        from dotenv import load_dotenv
        env_file = os.path.join(sts.project_dir, ".env")
        load_dotenv(env_file)

def clean_kwargs(*args, **kwargs):
    # kwargs might come from a LLM api and might be poluted with whitespaces ect.
    cleaned_kwargs = {}
    for k, vs in kwargs.items():
        if isinstance(vs, str):
            cleaned_kwargs[k.strip()] = vs.strip().strip("'")
        else:
            cleaned_kwargs[k.strip()] = vs
    return cleaned_kwargs

def check_missing_kwargs(*args, api,  **kwargs):
    """
    Uses arguments to check if all required kwargs are provided
    """
    missings = set()
    requireds = {}
    for k, v in requireds.items():
        if k not in kwargs.keys():
            missings.add(k)
    if missings:
        print(f"{Fore.RED}Missing required arguments: {missings}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Required arguments are: {requireds}{Style.RESET_ALL}")
        exit()

def get_package_data(*args, work_dir:str=None, **kwargs) -> dict:
    """
    Uses work_dir or cwd to detect package information such as project_dir, package_dir, ect.
    """
    work_dir = os.path.abspath(work_dir if work_dir is not None else os.getcwd())
    # traverses the directory structure to find project and package directories
    ctx = DirContext()(path=work_dir).__dict__
    # we only return a subset of the context information
    obj_names = {'pr_name', 'pg_name', 'work_dir', 'project_dir', 'package_dir', 'is_package'}
    pg_objs = {k: v for k, v in ctx.items() if k in obj_names}
    return pg_objs

def clean_paths(*args, **kwargs) -> dict:
    """
    WHY: Normalize *_dir/*_path and resolve missing files if path doesn't exist.
    """
    normalizeds = {}
    for n, v in kwargs.items():
        if isinstance(v, str) and any(t in n for t in {"_dir", "_path"}):
            normalizeds[n] = normalize_path(v, *args, **kwargs)
    return normalizeds

def normalize_path(path: str, *args, **kwargs) -> str:
    """
    WHY: Canonicalize user-supplied paths consistently across OS.
    """
    if not path:
        return path
    p = os.path.expanduser(path)
    if not os.path.isabs(p):
        p = os.path.abspath(os.path.join(os.getcwd(), p))
    return os.path.normpath(p)