# prompt_info.py
import os, jinja2, json, requests
import pyperclip as pc
from colorama import Fore, Style

import codeon.helpers.printing as printing
import codeon.contracts as contracts
from codeon.apis.info import main as info
import codeon.settings as sts


#-- cr_op: replace, cr_type: function, cr_anc: prompt_info, cr_id: 2025-10-14-19-59-41 --#
def prompt_info(*args, **kwargs) -> None:
    kwargs.update(contracts.update_params(*args, **kwargs))
    printing.pretty_dict('kwargs', kwargs)
    _cr_prompt = render_from_kwargs(*args,**kwargs).get('cr_prompt_template')
    # extract context block between from_split/to_split
    prompt = fmc(*args, prompt=_cr_prompt, **kwargs)
    prompt += get_guidlines(*args, **kwargs)
    prompt += f"\n# 3. Instructions:\n{_cr_prompt}\n"
    printing.pretty_prompt(prompt, *args, **kwargs)

def fmc(*args,  work_dir:str, source_path:str=None, work_file_name:str=None, prompt:str='None',
                verbose:int=None, integration_format:str='md', **kwargs):
    work_file_name = source_path if os.path.isfile(source_path) else work_file_name
    assert not any([s in prompt for s in sts.jinja_seps]), (
                                                f"propmt_info.fmc: invalid chars inside "
                                                f"jinja2 template: {sts.jinja_seps = }"
                                                    )
    r = str(requests.post(  f"{getattr(sts, 'model_ip', 'http://localhost')}:"
                            f"{getattr(sts, 'model_default_port', 9005)}/call/",
                            json={
                                    "api": 'prompt', 
                                    "work_dir": work_dir,
                                    "user_prompt": prompt,
                                    "work_file_name": work_file_name,
                                    "kwargs_defaults": 'codeon',
                                    "verbose": verbose,
                                    },
                            headers={"Accept": "application/json"}, 
                            timeout=60,
                    )
                    .json()
                    .get("response")
            )
    prompt = f"{sts.from_split}\n{r.rsplit(sts.from_split, 1)[-1].rsplit(sts.to_split, 1)[0]}"
    if integration_format == "md":
        prompt = prompt.split(sts.md_split)[0]
    return prompt

def get_guidlines(*args, verbose:int=0, **kwargs) -> str:
    if verbose >= 2:
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

def render_from_kwargs(*args, **kwargs) -> str:
    """for now we only have a single prompt template"""
    assert all([kwargs.get(f) for f in 
                                {'cr_prompt', 'cr_deliverable', 'integration_format'}]), (
                                                    f"prompt_info.render_from_kwargs: "
                                                    f"One of {r_fields = } is missing!"
                                                    )
    templates = {}
    for name, setting in sts.user_settings.items():
        if type(setting) != str:
            continue
        elif sts.jinja_seps[0] in setting:
            templates[name] = jinja2.Template(setting).render(kwargs)
    return templates

def main(*args, **kwargs):
    """
    Main function to retrieve and display prompt-related information.
    """
    return prompt_info(*args, **kwargs)

