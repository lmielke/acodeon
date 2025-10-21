# prompter.py
import jinja2, json, os, re, requests
import pyperclip as pc
from colorama import Fore, Style

import codeon.helpers.printing as printing
import codeon.contracts as contracts
from codeon.apis.info import main as info
import codeon.settings as sts


class Prompter:


    def __init__(self, *args, **kwargs):
        self.prompt = None

    #-- cr_op: replace, cr_type: function, cr_anc: prompt, cr_id: 2025-10-14-19-59-41 --#
    def __call__(self, *args, **kwargs) -> None:
        kwargs.update(contracts.update_params(*args, **kwargs))
        printing.pretty_dict('kwargs', kwargs)
        self.prompt = self.mk_prompt(*args, **kwargs)
        printing.pretty_prompt(self.prompt, *args, **kwargs)
        return self


    def mk_prompt(self, *args, api, work_file_name:str=None, **kwargs) -> str:
        _cr_prompt = self.render_from_kwargs(*args,**kwargs).get('cr_prompt_template')
        # extract context block between from_split/to_split
        self.work_file_name = self.set_work_file(*args, work_file_name=work_file_name, **kwargs)
        payload = Prompter.model_call_params(*args, api='prompt', 
                                                user_prompt=_cr_prompt, 
                                                work_file_name=self.work_file_name, **kwargs)
        prompt = Prompter.model_call(payload, *args, **kwargs)
        prompt = self.add_guidlines(prompt, *args, **kwargs)
        prompt += f"\n# 3. Instructions:\n{_cr_prompt}\n"
        return prompt

    @staticmethod
    def model_call_params(*args, api='prompt',
                                        work_dir:str,
                                        work_file_name:str,
                                        user_prompt:str='None',
                                        external_prompt:str=None,
                                        verbose:int=None,
        **kwargs):
        assert not any([s in user_prompt for s in sts.jinja_seps]), \
        f"propmt_info.model_call: invalid chars inside jinja2 template: {sts.jinja_seps = }"
        return {
                    "api": api, 
                    "work_dir": work_dir,
                    "user_prompt": user_prompt if not external_prompt else None,
                    "external_prompt": external_prompt,
                    "work_file_name": work_file_name,
                    "kwargs_defaults": 'codeon',
                    "verbose": verbose,
                    }

    @staticmethod
    def model_call(payload, *args, integration_format:str='md', **kwargs):
        # this calls altered bytes server on localhost
        r = str(requests.post(  f"{getattr(sts, 'model_ip', 'http://localhost')}:"
                                f"{getattr(sts, 'model_default_port', 9005)}/call/",
                                    json={**payload},
                                    headers={"Accept": "application/json"}, 
                                    timeout=60,
                        )
                        .json()
                        .get("response")
                )
        prompt = f"{sts.from_split}\n{r.rsplit(sts.from_split, 1)[-1].rsplit(sts.to_split, 1)[0]}"
        if integration_format == "md":
            prompt = prompt.split(sts.readme_split)[0]
        return prompt

    def set_work_file(self, *args, source_path:str=None, work_file_name:str=None, **kwargs) -> str:
        try:
            work_file_name = source_path if os.path.isfile(source_path) else work_file_name
        except TypeError:
            pass
        assert work_file_name, f"prompt.set_work_file: work_file_name is None or empty!"
        return work_file_name


    def add_guidlines(self, prompt:str, *args, verbose:int=0, **kwargs) -> str:
        findr = sts.readme_replace['installs'][0].strip('^')
        repls = sts.readme_replace['installs'][1]
        t_prompt = re.sub(findr, repls, prompt, flags=re.DOTALL | re.MULTILINE)
        if verbose >= 2:
            with open(sts.cq_ex_llm_file, "r", encoding="utf-8") as cq:
                guidelines = '\n' + cq.read() + '\n'
        else:
            guidelines = "\nNOTE: CQ:EX-LLM to generate professional python.\n"
        return jinja2.Template(t_prompt).render({'guidelines': guidelines})

    def print_info(self, out):
        print(      f"{Fore.GREEN}\nPrompt copied to clipboard:{Fore.RESET}"
                    f"\n'''{Style.DIM}{out[:160]}\n"
                    f"{Fore.BLUE}...{Style.RESET_ALL}\n"
                    f"{out[-160:]}\n'''")

    def render_from_kwargs(self, *args, **kwargs) -> str:
        """for now we only have a single prompt template"""
        pr_fields = {'cr_prompt', 'cr_deliverable', 'integration_format'}
        assert all([kwargs.get(f) for f in pr_fields]), (
                                                    f"prompt.render_from_kwargs: "
                                                    f"One of {pr_fields = } is missing!"
                                                        )
        templates = {}
        for name, setting in sts.user_settings.items():
            if type(setting) != str:
                continue
            elif sts.jinja_seps[0] in setting:
                templates[name] = jinja2.Template(setting).render(kwargs)
        return templates
