# prompt_info.py
import os, json, requests
import pyperclip as pc
from colorama import Fore, Style

import codeon.contracts as contracts
from codeon.apis.info import main as info
import codeon.settings as sts

def prompt_info(*args, **kwargs):
    kwargs = contracts.update_params(*args, **kwargs)
    up = 'Describe shortly what this package is doing!'
    prompt = fmc(up, kwargs.get('work_dir'), 'prompt')
    prompt += get_guidlines(*args, **kwargs)
    print(f"{kwargs.get('work_dir') = }")
    print(f"{prompt = }")
    # pc.copy(prompt)
    # print_info(prompt)

def fmc(prompt, cwd:str, api:str="thought", fmt:str='text') -> str:
    """
    Fast Model Connect - connect to altered bytes server for quick responses
    """
    # if model_ip is defined in the sts.globals then we take it else we assume localhost
    model_ip = getattr(sts, 'model_ip', 'http://127.0.0.1')
    model_default_port = getattr(sts, 'model_default_port', 9005)
    return str(requests.post( f"{model_ip}:{model_default_port}/call/",
                            json={
                                    "api": api, 
                                    "work_dir": cwd, 
                                    "user_prompt": prompt,
                                    "work_file_name": rf"{__file__}",
                                    "kwargs_defaults": 'codeon',
                                    "verbose": 1,
                                    },
                            headers={"Accept": "application/json"}, 
                            timeout=60,
                    )
                    .json()
                    .get("response")
            )

def get_guidlines(*args, verbose:int=0, **kwargs) -> str:
    if verbose:
        with open(sts.cq_ex_llm_file, "r", encoding="utf-8") as cq:
            guidelines = '\n' + cq.read() + '\n'
    else:
        guidelines = "\nNOTE: CQ:EX-LLM to generate professional python.\n"
    return guidelines

def print_info(out):
    print(      f"{Fore.GREEN}\nPrompt copied to clipboard:{Fore.RESET}"
                f"\n'''{Style.DIM}{out[:160]}\n"
                f"{Fore.BLUE}...{Style.RESET_ALL}\n"
                f"{out[-160:]}\n'''")

def main(*args, **kwargs):
    """
    Main function to retrieve and display prompt-related information.
    """
    return prompt_info(*args, **kwargs)

