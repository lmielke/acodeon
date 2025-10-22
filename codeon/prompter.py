# prompter.py
import ast, jinja2, json, os, re, requests
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


    def mk_prompt(self, *args, api, **kwargs) -> str:
        payload = Prompter.model_call_params(*args, api='prompt',
                # preliminary prompt for alter to work properly
                user_prompt=self.render(f"{sts.cr_sts['cr_title']}", **kwargs),
                **kwargs)
        _cr_prompt = self.render(   f"{sts.cr_sts['cr_title']}\n"
                                    f"{sts.cr_sts['cr_prefix']}", *args, **kwargs)
        _cr_prompt += Prompter.model_call(payload, *args, **kwargs)
        _cr_prompt = self.insert_guidlines(_cr_prompt, *args, **kwargs)
        _cr_prompt += self.render(  f"\n\n{sts.cr_sts['cr_prompt_head']}"
                                                f"\n{sts.cr_sts['cr_prompt']}\n"
                                                f"{sts.cr_sts['cr_suffix']}\n", **kwargs)
        _cr_prompt += self.add_entry_point(*args, **kwargs)
        return printing.clean_pipe_text(_cr_prompt)

    def add_entry_point(self, *args,    source_path:str=None,
                                            cr_op:str,
                                            cr_type:str = 'tbd',
                                            cr_anc:str = 'tbd',
        **kwargs) -> str:
        if cr_op is None or cr_op not in ['create', 'update']:
            return ''
        if source_path is not None:
            cr_anc = Prompter.class_names_from_file(path=source_path, *args, **kwargs)
        with open(sts.cr_integration_file_templ_path, "r", encoding="utf-8") as f:
            starting_string = ( f"```python\n"
                                f"{self.render(f.read(),
                                        cr_op=cr_op,
                                        cr_type=cr_type,
                                        cr_anc=cr_anc,
                                    **kwargs)}"
                                f"```\n"
                                )

        template = f"\n{sts.start_head}\n" + self.render(
                                                f"{sts.start_prefix}\n{sts.start_string}\n", 
                                                starting_string=starting_string, 
                                                        **kwargs)
        print(f"{Fore.YELLOW}{template}{Fore.RESET}")
        return template

    @staticmethod
    def class_names_from_file(path: str, *args, **kwargs) -> list[str]:
        """WHY: Parse classes without executing code (safe, fast)."""
        with open(path, "r", encoding="utf-8") as f:
            s = f.read()
        t = ast.parse(s, filename=path)
        return f"[{', '.join([n.name for n in ast.walk(t) if isinstance(n, ast.ClassDef)])}]"


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
        prompt = f"# {sts.from_split}\n{r.rsplit(sts.from_split, 1)[-1].rsplit(sts.to_split, 1)[0]}"
        if integration_format == "md":
            prompt = prompt.split(sts.readme_split)[0]
        return prompt

    def insert_guidlines(self, prompt:str, *args, verbose:int=0, **kwargs) -> str:
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

    def render(self, text, *args, **kwargs) -> str:
        """jinja2 renders a text using kwargs as context"""
        assert kwargs, "prompter.render: kwargs must not be empty."
        pr_fields = set(re.findall(r'{{\s*(\w+)\s*}}', text))
        context = {f: kwargs.get(f) for f in pr_fields}
        assert (pr_fields == context.keys()) \
                and all(context.values()), (f"prompter.render: missing fields in kwargs: "
                                            f"{pr_fields = }, {context = }")
        return jinja2.Template(text).render(context) + '\n'
