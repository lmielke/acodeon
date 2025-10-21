"""
codeon.py
This is an example module for a properly formatted Python codeontype project.
It contains the Codeon used for codeontyping Python projects.
"""

# Standard library imports in alphabetical order
# Local application imports in alphabetical order
import codeon.settings as sts
import codeon.helpers.printing as printing
from codeon.prompter import Prompter
import codeon.contracts as contracts


class Codeon:
    """
    Codeon is a class for codeontyping Python projects.
    NOTE: **kwargs are critical in this class to allow for the passing of arguments
    """

    def __init__(self, *args, **kwargs) -> None:
        """
        Initializes Codeon with the following attributes.
        """
        self.p = Prompter(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        kwargs = contracts.checks(*args, **kwargs)
        self.p(*args, **kwargs)
        self.get_response(*args, **kwargs)
        return self

    def get_response(self, *args, api, **kwargs) -> str:
        payload = Prompter.model_call_params(*args, 
                                                api='thought', 
                                                work_file_name=self.p.work_file_name,
                                                external_prompt=self.p.prompt, 
                                                **kwargs)
        r = Prompter.model_call(payload, *args, **kwargs)
        printing.pretty_prompt(r, *args, **kwargs)

