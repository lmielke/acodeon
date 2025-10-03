import os
import json
from dataclasses import asdict
from colorama import Fore, Style

import codeon.contracts as contracts
from codeon.helpers.collections import temp_chdir
from codeon.helpers.file_info import UpdatePaths
import codeon.settings as sts
from codeon.apis.update import _archive_op_code_file


# Add this import at the top of the file
from codeon.creator import JsonEngine, CreateEngine

def _stage_from_json(*args, op_code_dir: str, **kwargs) -> dict:
    """Parses a JSON string using the JsonEngine and writes the content."""
    engine = JsonEngine(*args, **kwargs)
    data = engine.parse(*args, **kwargs)
    if not data:
        print(f"{Fore.RED}Failed to parse JSON string after all strategies.{Style.RESET_ALL}")
        return False
    try:
        target_filename = data["target"]
        code_content = data["code"]
        create_path = os.path.join(op_code_dir, target_filename)
        with open(create_path, "w", encoding="utf-8") as f:
            f.write(code_content)
        print(
            f"{Fore.GREEN}Successfully staged op-code file at: {Style.RESET_ALL}"
            f"{create_path.replace(os.path.expanduser('~'), '~')}"
        )
        return create_path
    except KeyError as e:
        print(f"{Fore.RED}Parsed JSON is missing required key: {e}{Style.RESET_ALL}")
        return False
    except IOError as e:
        print(f"{Fore.RED}Error writing file to {create_path}: {e}{Style.RESET_ALL}")
        return False

def _create(*args, work_dir: str = None, **kwargs):
    """
    Orchestrates the staging of a new op-code file from a JSON source.
    Returns a status dictionary.
    """
    if work_dir is None:
        kwargs = contracts.checks(*args, api="create", **kwargs)
        work_dir = kwargs['work_dir']
    path_fields = UpdatePaths.__dataclass_fields__.keys()
    paths = UpdatePaths(**{k: v for k, v in kwargs.items() if k in path_fields})
    if not paths.op_code_dir:
        print(f"{Fore.RED}Error: Could not determine op_code_dir.{Style.RESET_ALL}")
        return None
    status_dict = None
    with temp_chdir(work_dir or kwargs.get("work_dir")):
        kwargs.update(asdict(paths))
        path_updates = UpdatePaths._create_paths(_stage_from_json(*args, **kwargs), **kwargs)
        kwargs.update(path_updates)
        # we now use the staged code file to create the final code file in target dir
        status_dict = CreateEngine(*args, **kwargs).run(*args, **kwargs)
    # --- Post-processing ---
    if status_dict and status_dict.get("ch_id"):
        _archive_op_code_file(*args, **kwargs) # TODO: Implement or import
        pass
    else:
        print(f"{Fore.RED}create._create Error: File creation failed.{Style.RESET_ALL}")
    # _log_result(*args, status=bool(status_dict), **kwargs) # TODO: Implement or import
    return status_dict


def main(*args, **kwargs):
    """Main entry point for the 'create' API."""
    return _create(*args, **kwargs)