# C:\Users\lars\python_venvs\packages\acodeon\codeon\updater.py
import os, shutil
from colorama import Fore, Style

import codeon.contracts as contracts
from codeon.cr_info import CrData

from codeon.headers import CR_OPS_PG
from codeon.creator import JsonEngine, IntegrationEngine, ProcessEngine, PromptEngine
import codeon.settings as sts
import codeon.helpers.printing as printing



class Updater:
    """Orchestrates the create and update refactoring processes."""
    default_up_to_phase:str = 'cr_processing'
    default_entry_phase:str = 'cr_json'
    # PromptEngine to be implemented
    engines = (PromptEngine, JsonEngine, IntegrationEngine, ProcessEngine)
    phases = dict(zip(sts.phases, engines))
    phase_enum = {p:i for i,p in enumerate(sts.phases)}

    def __init__(self, *args, api: str, **kwargs):
        self.api = api
        self.status_dict = {}
        self.cr_data: CrData = None
        self.cr_fields = lambda kwargs: {k: v for k, v in kwargs.items() if k in CrData.__dataclass_fields__}

    def __call__(self, *args, entry_phase:str=None, up_to_phase:str=None, verbose:int=0, 
        **kwargs) -> dict:
        """
        Main loop to run the update phases sequentially as defined in cls.phases. 
        """
        up_to_phase = up_to_phase if up_to_phase is not None else self.default_up_to_phase
        entry_phase = entry_phase if entry_phase is not None else self.default_entry_phase
        kwargs = self.update_params(*args, up_to_phase=up_to_phase, entry_phase=entry_phase, **kwargs)
        for i, (phase, engine) in enumerate(self.phases.items()):
            printing.pretty_dict(f"{i}: Updater.{phase}", kwargs)
            if self.phase_enum[entry_phase] <= i <= self.phase_enum[up_to_phase]:
                if verbose:
                    print(  f"{Fore.MAGENTA}{i}: # Updater.__call__: Running phase '{phase}' "
                            f"with engine '{engine.__name__}'...{Fore.RESET}")
                if engine:
                    kwargs.update(self.cr_phase(phase, engine, *args, **kwargs))
        return self.cr_data.to_dict()

    def cr_phase(self, phase, engine, *args, **kwargs) -> dict | None:
        # 1. Use JsonEngine to parse and validate the model output
        eng = engine(*args, **kwargs)(*args, **kwargs)
        if eng.cr_file_exists == (False or None):
            return {'status': 'JSON parsing failed or was empty. No json file saved.'}
        elif eng.cr_file_exists == sts.file_exists_default:
            # generic engine variables must be mapped to phase specific names
            kwargs[f"{phase}_path"] = eng.cr_path
            kwargs[f"{phase}_file_exists"] = eng.cr_file_exists
            return self.update_params(eng.__dict__, *args, **kwargs)
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

