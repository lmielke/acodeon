# C:\Users\lars\python_venvs\packages\acodeon\codeon\updater.py
import os, shutil
from colorama import Fore, Style
from codeon.helpers.printing import logprint, Color, MODULE_COLORS
MODULE_COLORS["updater"] = Color.BLUE

import codeon.contracts as contracts
from codeon.cr_info import CrData

from codeon.creator import SourceEngine
import codeon.settings as sts
import codeon.helpers.printing as printing



class Updater:
    """Orchestrates the create and update refactoring processes."""
    default_up_to_phase:str = 'processing'
    default_entry_phase:str = 'json'
    # PromptEngine to be implemented
    phases = {p:i for i,p in enumerate(sts.phases)}

    def __init__(self, *args, api: str, **kwargs):
        self.api = api
        self.status_dict = {}
        self.cr_data: CrData = None

    def __call__(self, *args, entry_phase:str=None, up_to_phase:str=None, verbose:int=0, 
        **kwargs) -> dict:
        """
        Main loop to run the update phases sequentially as defined in cls.phases. 
        """
        up_to_phase = up_to_phase if up_to_phase is not None else self.default_up_to_phase
        entry_phase = entry_phase if entry_phase is not None else self.default_entry_phase
        kwargs.update(self.update_params(*args, up_to_phase=up_to_phase,
                                                entry_phase=entry_phase,
                                                **kwargs
                        )
        )
        for i, phase in enumerate(sts.phases):
            logprint(f"# {i}: RUN {phase.upper()}")
            if self.phases[entry_phase] <= i <= self.phases[up_to_phase]:
                kwargs.update(self.cr_phase(phase, *args, verbose=verbose, **kwargs))


            if phase == 'prompt': exit()
        

        return self.cr_data.to_dict()

    def cr_phase(self, phase, *args, verbose:int=0, **kwargs) -> dict | None:
        # 1. Use SourceEngine to parse and validate the model output
        phase_pars = self.get_phase_params(phase, *args, **kwargs)
        if verbose >=2:
            printing.pretty_dict(f"Updater.{phase.upper()}.phase_pars going in ...", phase_pars)
        data = SourceEngine(phase, *args, **phase_pars)(*args, **phase_pars)
        if not data.get('work_file_name'):
            self.error_handling(phase, *args, **kwargs)
        return self.update_params(data, *args, **kwargs)

    def get_phase_params(self, phase, *args, **kwargs) -> dict:
        phase_pars = {k.replace(f'{phase}_', ''): vs for k, vs in kwargs.items() if phase in k}
        phase_pars.update({k: vs for k, vs in kwargs.items() if k in SourceEngine.fields})
        phase_pars.update({k:vs for k, vs in kwargs.items() if 'path' in k})
        if not kwargs.get('string'):
            phase_pars['string'] = kwargs.get(f"{phase}_string", None)
        return phase_pars

    def update_params(self, new_params:dict=None, *args, **kwargs):
        if new_params is not None:
            kwargs.update(new_params)
        kwargs = contracts.update_params(*args, **kwargs)
        if self.cr_data is None:
            self.cr_data = CrData(*args, **CrData.fields(*args, **kwargs))
            kwargs.update(self.cr_data.to_dict())
        else:
            kwargs.update(self.cr_data.update_data(*args, **kwargs))
        return kwargs

    def error_handling(phase, *args, **kwargs):
        msg = f"{phase} parsing failed or was empty. No json file saved."
        logprint(msg, level='error')
        raise RuntimeError(msg)
