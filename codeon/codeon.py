"""
codeon.py
Handles a codeon CR (Change Request) from start to finish.
"""
import os, re
import pyperclip as pc
from colorama import Fore, Style
import codeon.settings as sts
import codeon.helpers.printing as printing
import codeon.contracts as contracts
from codeon.cr_info import CrData
from codeon.prompter import PromptEngine
from codeon.helpers.string_parser import JsonParser, MdParser

from codeon.updater import Updater


class Codeon:


    def __init__(self, *args, **kwargs) -> None:
        self.cr_data: CrData = None
        self.CR = PromptEngine(*args, **kwargs)
        self.cr_fields = lambda kwargs: {k: v for k, v in kwargs.items() if k in CrData.__dataclass_fields__}

    def __call__(self, *args, **kwargs):
        kwargs.update(self.identify_entry_source(*args, **kwargs))
        kwargs = self.update_params(*args, **kwargs)
        printing.pretty_dict('codeon.main.kwargs', kwargs)
        r = Updater(*args, **kwargs)(*args, **kwargs)
        printing.pretty_dict('update.main.r', r)


    def identify_entry_source(self, *args, 
        cr_prompt:str=None, cr_entry_source:str=None, entry_phase:str=None, **kwargs):
        """
        Takes the cr_entry_source and identifies its character to determine what to do with it
        """
        # if cr_entry_source is a file path, we dont handle it here
        if not cr_entry_source:
            entry_phase = entry_phase if entry_phase is not None else sts.phases[0]
            return {'entry_phase': entry_phase}
        elif match:= re.compile(sts.cr_file_regex).match(cr_entry_source):
            f_parts = match.groupdict()
            entry_phase = entry_phase if entry_phase is not None else sts.phases[1]
            return {'entry_phase': entry_phase}
        elif match:= re.compile(sts.file_regex).match(cr_entry_source):
            f_parts = match.groupdict()
            entry_phase = entry_phase if entry_phase is not None else sts.phases[1]
            return {'entry_phase': entry_phase}
        # now we check if cr_entry_source is a text of some sort
        if cr_entry_source.strip().lower() == 'clip':
            text = pc.paste()
            assert text.strip(), print(f"{Fore.RED}-c 'clip' clipboard is empty!{Fore.RESET}")
            print(f"{Fore.MAGENTA}Codeon.identify_entry_source: Using clipboard! {Fore.RESET}")
        else:
            text = cr_entry_source
        # lets find out if text is a json_string
        if MdParser(*args, md_string=text)():
            entry_phase = entry_phase if entry_phase is not None else sts.phases[0]
            return {'entry_phase': entry_phase, 'cr_integration_string' : text}
        elif JsonParser(*args, json_string=text)():
            entry_phase = entry_phase if entry_phase is not None else sts.phases[1]
            return {'entry_phase': entry_phase, 'json_string' : text}
        else:
            if cr_prompt:
                print(f"{Fore.YELLOW}Codeon.identify_entry_source: Overwriting existing "
                      f"{cr_prompt = }{Fore.RESET}")
            entry_phase = entry_phase if entry_phase is not None else sts.phases[0]
            return {'entry_phase': entry_phase, 'cr_prompt' : text}

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

