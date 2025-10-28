# C:\Users\lars\python_venvs\packages\acodeon\codeon\updater.py
import os, shutil
from colorama import Fore, Style

import codeon.contracts as contracts
from codeon.helpers.cr_info import CrData

from codeon.headers import OP_P
from codeon.creator import JsonEngine, IntegrationEngine, ProcessEngine
import codeon.settings as sts
import codeon.helpers.printing as printing


class Updater:
    """Orchestrates the create and update refactoring processes."""

    def __init__(self, *args, api: str, **kwargs):
        self.api = api
        self.status_dict = {}
        self.cr_data: CrData = None
        self.cr_fields = lambda kwargs: {k: v for k, v in kwargs.items() if k in CrData.__dataclass_fields__}


    def __call__(self, *args, verbose:int=0, **kwargs) -> dict | None:
        """Main execution flow for both 'create' and 'update' APIs."""
        kwargs = self.update_params(*args, **kwargs)
        self.run(*args, **kwargs)
        return self.cr_data.to_dict()

    def run(self, *args, current_phase:str, **kwargs) -> dict | None:
        # skp phases before current_phase currently not implemented
        kwargs.update(self.cr_json(*args, **kwargs))
        kwargs.update(self.cr_integration(*args, **kwargs))
        kwargs.update(self.cr_processing(*args, **kwargs))

    def cr_json(self, *args, json_string:str=None, **kwargs) -> dict | None:
        # 1. Use JsonEngine to parse and validate the model output
        je = JsonEngine(*args, json_string=json_string, **kwargs)(*args, **kwargs)
        if je.cr_json_file_exists == (False or None):
            return {'status': 'JSON parsing failed or was empty. No json file saved.'}
        elif je.cr_json_file_exists == sts.file_exists_default:
            return self.update_params(je.__dict__, *args, **kwargs)
        else:
            return {}
        
    def cr_integration(self, *args, **kwargs) -> dict | None:
        # 2. Use IntegrationEngine to clean and stage the file
        ie = IntegrationEngine(*args, **kwargs)(*args, **kwargs)
        if ie.cr_integration_file_exists == (False or None):
            return {'status': 'Integration creation failed. No integration file saved.'}
        elif ie.cr_integration_file_exists == sts.file_exists_default:
            return self.update_params(ie.__dict__, *args, **kwargs)
        else:
            return {}
        
    def cr_processing(self, *args, **kwargs) -> dict | None:
        # 3. Process the change request
        pe = ProcessEngine(*args, **kwargs)(*args, **kwargs)
        if pe.cr_processing_file_exists == (False or None):
            return {'status': 'Processing failed. No staging file saved.'}
        elif pe.cr_processing_file_exists == sts.file_exists_default:
            return self.update_params(pe.__dict__, *args, **kwargs)
        else:
            return {}

    def update_params(self, new_params:dict=None, *args, **kwargs):
        if new_params is not None:
            kwargs.update(new_params)
        kwargs = contracts.update_params(*args, **kwargs)
        if self.cr_data is None:
            self.cr_data = CrData(*args, **self.cr_fields(kwargs))
            kwargs.update(self.cr_data.to_dict())
        else:
            kwargs.update(self.cr_data.update_data(*args, **kwargs))
        return kwargs

