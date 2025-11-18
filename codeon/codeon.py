"""
codeon.py
Handles a codeon CR (Change Request) from start to finish.
"""
import os, re
import pyperclip as pc
from colorama import Fore, Style
import codeon.settings as sts
import codeon.helpers.printing as printing
from codeon.helpers.printing import logprint, Color, MODULE_COLORS
MODULE_COLORS["codeon"] = Color.CYAN
import codeon.helpers.collections as collections
import codeon.contracts as contracts
from codeon.cr_info import CrData
# from codeon.prompter import PromptEngine
from codeon.helpers.string_parser import JsonParser, MdParser

from codeon.updater import Updater


class Codeon:
    """
    Identifies CR source and creates/updates the CR through the Updater class.
    A source generally refers to a existing or new package file. A update refers to 
    some change to be made to the source package.
    """
    

    def __init__(self, *args, **kwargs) -> None:
        self.entry_phase = None
        self.update_source = None
        self.update_source_type = None
        self.cr_data: CrData = None

    def __call__(self, *args, **kwargs):
        kwargs.update(self.parse_update_source(*args, **kwargs))
        kwargs.update(self.set_entry_phase(*args, **kwargs))
        kwargs = self.update_params(*args, **kwargs)
        r = Updater(*args, **kwargs)(*args, **kwargs)
        return r


    def parse_update_source(self, *args, 
                                            prompt_string:str=None,
                                            update_source:str=None,
                                            entry_phase:str=None, 
                                            verbose:int=0, 
        **kwargs):
        """
        Takes the update_source and gets relevant runtime infos
        """
        # if update_source is a file path, we dont handle it here
        if verbose:
            printing.pretty_dict('codeon.parse_update_source.kwargs', kwargs)
        if update_source is None:
            return {}
        if update_source.strip().lower() == 'clip':
            text = pc.paste()
            text = printing.strip_ansi_codes(text.strip())
            assert text, logprint("-c clip is empty!", level='error')
            update_source, update_source_type = text, 'text'
            print(f"{Fore.MAGENTA}Codeon.parse_update_source: Using clipboard! {Fore.RESET}")
        elif m := collections.match_file_info(update_source):
            file_name = collections.to_file_name(m)
            if update_source == file_name:
                update_source_type = 'file'
            else:
                prompt_string += ('\n' + update_source)
        print(f"{update_source = }, {update_source_type = }")
        return {'update_source': update_source,
                'update_source_type': update_source_type,
                'prompt_string': prompt_string,
                }

    def set_entry_phase(self, *args, prompt_string:str=None, **kwargs):
        if prompt_string:
            self.entry_phase = sts.phases[0]
        else:
            self.entry_phase = sts.phases[1]
        logprint(f"{prompt_string = } {self.entry_phase = }", level='info')
        return {'entry_phase': self.entry_phase}

    def update_params(self, new_params:dict=None, *args, verbose:str=0, **kwargs):
        if verbose:
            printing.pretty_dict('codeon.update_params.kwargs', kwargs)
        if new_params is not None:
            kwargs.update(new_params)
        kwargs = contracts.update_params(*args, **kwargs)
        if self.cr_data is None:
            self.cr_data = CrData(*args, **CrData.fields(*args, **kwargs))
            kwargs.update(self.cr_data.to_dict())
        else:
            kwargs.update(self.cr_data.update_data(*args, **kwargs))
        kwargs['verbose'] = verbose
        return kwargs
