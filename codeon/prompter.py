# prompter.py
import ast, jinja2, json, os, re, requests
import pyperclip as pc
from colorama import Fore, Style

import codeon.helpers.printing as printing
import codeon.contracts as contracts
from codeon.apis.info import main as info
import codeon.settings as sts

from codeon.creator import IntegrationEngine


class PromptEngine:


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
        pre_p = self.render(f"{sts.cr_sts['cr_title']}\n{sts.cr_sts['cr_prefix']}", **kwargs)
        user_prompt=self.render(f"{sts.cr_sts['cr_title']}", **kwargs)
        # first model call to get base prompt with context
        payload = PromptEngine.mk_payload(*args, api='prompt', user_prompt=user_prompt, **kwargs)
        pre_p += PromptEngine.model_call(payload, *args, **kwargs)
        # main prompt construction
        prompt = self.insert_guidelines(pre_p, *args, **kwargs)
        prompt += self.render(  f"\n\n{sts.cr_sts['cr_prompt_head']}"
                                    f"\n{sts.cr_sts['cr_prompt']}\n"
                                    f"{sts.cr_sts['cr_suffix']}\n", **kwargs)
        prompt += self.add_entry_point(*args, **kwargs)
        return printing.clean_pipe_text(prompt)

    def add_entry_point(self, *args, source_path:str=None,
            cr_op:str,
            cr_type:str='tbd',
            cr_anc:str='tbd',
        **kwargs) -> str:
        if cr_op is None or cr_op not in ['create', 'update']:
            return ''
        if source_path is not None:
            cr_anc = PromptEngine.class_names_from_file(path=source_path, *args, **kwargs)
        with open(sts.cr_integration_file_templ_path, "r", encoding="utf-8") as f:
            code = f"{self.render(f.read(), cr_op=cr_op, cr_type=cr_type, cr_anc=cr_anc, **kwargs)}"
        # entry point explain for the model to know what we expect
        template = self.render(f"\n{sts.start_head}\n{sts.start_prefix}\n{sts.start_string}\n", 
                                start_string=code, **kwargs)
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
    def mk_payload(*args, api='prompt', work_dir:str, work_file_name:str, verbose:int=None,
                                        user_prompt:str='None',
                                        external_prompt:str=None,
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

    def insert_guidelines(self, prompt:str, *args, verbose:int=0, **kwargs) -> str:
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
        assert kwargs, "PromptEngine.render: kwargs must not be empty."
        pr_fields = set(re.findall(r'{{\s*(\w+)\s*}}', text))
        context = {f: kwargs.get(f) for f in pr_fields}
        assert (pr_fields == context.keys()) \
                and all(context.values()), (f"prompter.render: missing fields in kwargs: "
                                            f"{pr_fields = }, {context = }")
        return jinja2.Template(text).render(context) + '\n'

    def create_cr_file(self, *args, work_file_name:str, cr_id:str, pg_name:str, **kwargs) -> None:
        printing.pretty_dict('kwargs', kwargs)
        cr_prompt_dir = sts.cr_prompt_dir(pg_name)
        cr_prompt_file_name = sts.cr_prompt_file_name(work_file_name, cr_id)
        with open(os.path.join(cr_prompt_dir, cr_prompt_file_name), 'w', encoding='utf-8') as f:
            f.write(self.prompt)

    def model_create_cr(self, *args, api, **kwargs) -> str:
        self.create_cr_file(*args, **kwargs)
        payload = self.mk_payload(*args, api='thought', external_prompt=self.prompt,
                                        **kwargs)
        r = self.model_call(payload, *args, **kwargs)
        printing.pretty_prompt(r, *args, **kwargs)
        self.create_integration_file(r, *args, **kwargs)

    def create_integration_file(self, r: str, *args, **kwargs) -> None:
        """Cleans and stages the raw model output."""
        printing.pretty_dict('kwargs', kwargs)
        ie = IntegrationEngine(*args, content=r, **kwargs)(*args, **kwargs)
