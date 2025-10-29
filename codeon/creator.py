"""
"""
import ast, jinja2, os, re, json, requests, shutil, subprocess
import libcst as cst
from colorama import Fore, Style
import pyperclip as pc

import codeon.settings as sts
from codeon.transformer import ApplyChangesTransformer
from codeon.parsers import CSTSource, CSTDelta
from codeon.helpers.string_parser import JsonParser, MdParser
import codeon.helpers.printing as printing


class JsonEngine:
    """
    Handles JSON payload for Change Requests (CRs).
    WHY: Delegates parsing to JsonParser and manages CR file creation/state.
    """

    def __init__(self, *args, json_string: str, cr_json_path: bool = False, **kwargs):
        self.json_string = json_string
        self.data: dict | None = None # Simplified annotation
        self.cr_path, self.cr_file_exists = cr_json_path, False
        self.work_file_name = None
        self.content = None

    def __call__(self, *args, json_string:str, **kwargs) -> "JsonEngine":
        self.read_cr_file(*args, **kwargs)
        if not self.json_string:
            return self
        self.data = JsonParser(*args, json_string=self.json_string, **kwargs)()
        if not self.data:
            return self
        self.cr_path, self.work_file_name = self.get_path(*args, **kwargs)
        self.write_json(*args, **kwargs)
        self.content = self.data.get(sts.json_content)
        return self

    def read_cr_file(self, *args, **kwargs) -> None:
        if not self.cr_path or not os.path.exists(str(self.cr_path)):
            return
        print(f"{Fore.MAGENTA}JsonEngine.__call__: JSON path already exists, "
              f"skipping parsing, loading instead.{Fore.RESET}")
        with open(self.cr_path, "r", encoding="utf-8") as f_json:
            self.json_string = f_json.read()

    def get_path(self, *args, pg_name: str, cr_id: str, **kwargs) -> tuple[str, str]:
        """Derives the full CR JSON file path and the target filename."""
        work_file_name = self.data.get(sts.json_target)
        cr_json_path = os.path.join(sts.cr_jsons_dir(pg_name),
                                    sts.cr_json_file_name(work_file_name, cr_id))
        return cr_json_path, work_file_name

    def write_json(self, *args, **kwargs) -> None:
        """Writes the parsed JSON string to the CR path."""
        if os.path.exists(str(self.cr_path)):
            print(f"{Fore.MAGENTA}JsonEngine.write_json: JSON file already exists as "
                  f"{os.path.basename(self.cr_path)}, skipping write. "
                  f"\nNOTE: Consider writing a new CR, "
                  f"if you want to update.{Fore.RESET}")
        else:
            with open(self.cr_path, "w", encoding="utf-8") as f_json:
                f_json.write(self.json_string)
        self.cr_file_exists = sts.file_exists_default


class IntegrationEngine:
    """
    Handles cleaning and staging of the cr_integration_file content
    extracted from a JSON payload.
    WHY: Separates file staging/cleaning from JSON parsing.
    """

    def __init__(self, *args, work_file_name: str, content: str=None,
                             cr_integration_file_exists:bool=False,**kwargs):
        assert content or cr_integration_file_exists, (
                            f"{Fore.RED}IntegrationEngine.__init__:{Fore.RESET} "
                            f"either content or cr_integration_file_exists must be set.")
        self.raw_content = content
        self.work_file_name = work_file_name
        self.cleaned_content = None
        self.cr_path = None
        self.cr_file_exists = cr_integration_file_exists

    def __call__(self, *args, cr_id: str, pg_name: str, **kwargs ) -> "IntegrationEngine":
        if self.cr_file_exists:
            print(  f"{Fore.MAGENTA}IntegrationEngine.__call__: Integration path "
                    f"already exists, skipping integrating.{Fore.RESET}")
            return self

        # Use the new MdParser to clean and validate the content
        # FIX: The MdParser instance must be called to return the cleaned string content.
        md_parser = MdParser(*args, md_string=self.raw_content)
        self.cleaned_content = md_parser(*args, **kwargs) # <-- CHANGE IS HERE

        if not self.cleaned_content:
            self.cr_file_exists = False
            return self

        self._write_content(*args, **kwargs)
        return self

    def _write_content(self, *args, cr_integration_path:str, **kwargs):
        """Writes the cleaned content to the staged path."""
        with open(cr_integration_path, "w", encoding="utf-8") as f:
            f.write(self.cleaned_content)
        self.cr_file_exists = sts.file_exists_default


class ProcessEngine:

    def __init__(self, *args, cr_processing_file_exists:bool=False, **kwargs):
        self.csts = CSTSource(*args, **kwargs)
        self.cstd = CSTDelta(*args, **kwargs)
        self.F = Validator_Formatter()
        self.cr_path, self.cr_file_exists = None, cr_processing_file_exists
        self.status_dict = {}

    def __call__(self, *args, work_dir, cr_integration_path, source_path, pg_op:str=None, 
        **kwargs):
        self.csts(*args, source_path=source_path,  **kwargs)
        self.cstd(*args, source_path=cr_integration_path, **kwargs)
        pg_op, cr_ops = self.cstd.body
        self.pg_op = pg_op.cr_op if pg_op else None
        tf = ApplyChangesTransformer(self.csts.body, cr_ops, *args, pg_op=pg_op, **kwargs)
        out_code = self.F(self.csts.body.visit(tf).code, *args, **kwargs)
        self._write_output(out_code, *args, source_path=source_path, **kwargs)
        return self

    def _write_output(self, code: str, *args, 
        source_path:str, cr_processing_path:str, cr_restore_path:str, hot:bool, **kwargs) -> bool:
        """Writes the final transformed code to the target file path."""
        with open(cr_processing_path, "w", encoding="utf-8") as f:
            f.write(code)
        # if source_file is overwritten we first backup the existing file for potential restore
        if hot and source_path:
            shutil.copyfile(source_path, cr_restore_path)
            # then we write the new code
            print(f"{Fore.MAGENTA}Updater._write_to source_path:{Fore.RESET} {source_path = }")
            with open(source_path, "w", encoding="utf-8") as f:
                f.write(code)
            self.cr_file_exists = sts.file_exists_default
        self.cr_file_exists = sts.file_exists_default


class PromptEngine:


    def __init__(self, *args, cr_prompt_file_exists:bool=False, **kwargs):
        self.prompt = None
        self.cr_path = None
        self.content = None
        self.cr_file_exists = cr_prompt_file_exists

    #-- cr_op: replace, cr_type: function, cr_anc: prompt, cr_id: 2025-10-14-19-59-41 --#
    def __call__(self, *args, **kwargs) -> None:
        # printing.pretty_dict('kwargs', kwargs)
        self.prompt = self.mk_prompt(*args, **kwargs)
        self.content = self.model_create_cr(*args, **kwargs)
        # printing.pretty_prompt(self.prompt, *args, **kwargs)
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
        # printing.pretty_dict('kwargs', kwargs)
        cr_prompt_dir = sts.cr_prompt_dir(pg_name)
        cr_prompt_file_name = sts.cr_prompt_file_name(work_file_name, cr_id)
        with open(os.path.join(cr_prompt_dir, cr_prompt_file_name), 'w', encoding='utf-8') as f:
            f.write(self.prompt)
        self.cr_file_exists = sts.file_exists_default

    def model_create_cr(self, *args, api, **kwargs) -> str:
        self.create_cr_file(*args, **kwargs)
        payload = self.mk_payload(*args, api='thought', external_prompt=self.prompt,
                                        **kwargs)
        r = self.model_call(payload, *args, **kwargs)
        return r


class Validator_Formatter:
    """
    Keeps output code and, if requested, formats via Black.
    WHY: Wire CLI flag reliably; avoid surprises if Black is absent.
    """

    def __init__(self, *args, **kwargs):
        self.out_code: str = ""

    def __call__(self, code: str, *args, use_black: bool = False, **kwargs) -> str:
        self.out_code = code
        if use_black:
            self._format_with_black(*args, **kwargs)
        return self.out_code

    def _format_with_black(self, *args, verbose: int = 0, **kwargs) -> None:
        import shutil, subprocess
        if not shutil.which("black"):
            if verbose >= 1:
                print("WARNING: --black set, but 'black' not found in PATH.")
            return
        try:
            p = subprocess.run(
                ["black", "-q", "-"],
                input=self.out_code,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if p.returncode == 0 and p.stdout:
                self.out_code = p.stdout
            elif verbose >= 1:
                print("WARNING: black returned non-zero; keeping unformatted code.")
        except Exception as e:
            if verbose >= 1:
                print(f"Error running black: {e}")
