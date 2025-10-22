"""
codeon.py
Handles a codeon CR (Change Request) from start to finish.
"""
import os
import codeon.settings as sts
import codeon.helpers.printing as printing
from codeon.prompter import Prompter
import codeon.contracts as contracts


class Codeon:


    def __init__(self, *args, **kwargs) -> None:
        self.cr = Prompter(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        kwargs = contracts.checks(*args, **kwargs)
        self.cr(*args, **kwargs)
        kwargs.update(contracts.update_params(*args, **kwargs))
        self.create_cr_file(*args, **kwargs)
        self.model_create_cr(*args, **kwargs)
        return self

    def model_create_cr(self, *args, api, **kwargs) -> str:
        payload = Prompter.model_call_params(*args, 
                                                api='thought', 
                                                external_prompt=self.cr.prompt, 
                                                **kwargs)
        r = Prompter.model_call(payload, *args, **kwargs)
        printing.pretty_prompt(r, *args, **kwargs)
        self.create_integration_file(r, *args, **kwargs)

    def create_cr_file(self, *args, work_file_name:str, cr_id:str, pg_name:str, **kwargs) -> None:
        printing.pretty_dict('kwargs', kwargs)
        cr_prompt_dir = sts.cr_prompt_dir(pg_name)
        cr_prompt_fiel_name = sts.cr_prompt_file_name(work_file_name, cr_id)
        with open(os.path.join(cr_prompt_dir, cr_prompt_fiel_name), 'w', encoding='utf-8') as f:
            f.write(self.cr.prompt)

    def create_integration_file(self, r, *args, work_file_name:str, cr_id:str, pg_name:str, **kwargs) -> None:
        printing.pretty_dict('kwargs', kwargs)
        cr_integration_dir = sts.cr_integration_dir(pg_name)
        # cr_integration_file_name = sts.cr_integration_file_name(work_file_name, cr_id)
        with open(os.path.join(cr_integration_dir, work_file_name), 'w', encoding='utf-8') as f:
            f.write(r)