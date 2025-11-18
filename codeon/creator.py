"""
"""
import jinja2, os, re, json, requests, shutil, subprocess
import libcst as cst
from colorama import Fore, Style
from codeon.helpers.printing import logprint, Color, MODULE_COLORS
MODULE_COLORS["creator"] = Color.MAGENTA

import codeon.settings as sts
from codeon.transformer import Transformer
from codeon.parsers import CSTSource, CSTDelta
from codeon.helpers.string_parser import JsonParser, MdParser
import codeon.helpers.printing as printing
import codeon.helpers.collections as collections


class SourceEngine:
    """
    Handles JSON payload for Change Requests (CRs).
    WHY: Delegates parsing to JsonParser and manages CR file creation/state.
    """
    fields = ['string', 'data', 'update_source', 'update_source_type', 'file_exists', 
                'pg_name', 'cr_id', 'cr_op', 'verbose', 'api', 'work_dir', 'work_file_name']

    def __init__(self, phase, *args, path = False, **kwargs):
        self._phase:str = phase
        self.update_source_type:str = None
        self.string:str = None
        self.path:str = path
        self.file_exists: bool = False
        self.work_file_name:str = None
        self.data: dict = None
        self.handler = FileHandler(phase, *args, **kwargs)
        self.prosessor = ProcessEngine(phase, *args, **kwargs)

    def __call__(self, *args, **kwargs) -> dict:
        self.veryfy_source(*args, **kwargs)
        printing.pretty_dict('SourceEngine.__dict__', self.__dict__)
        self.parse_source(*args, **kwargs)
        return self.processing(*args, **kwargs)

    def processing(self, *args, **kwargs) -> dict:
        self.path = self.handler.get_path(self.work_file_name, *args, **kwargs)
        logprint(f"{self._phase} path: {self.path}", level='dev')
        if self.update_source_type == 'string':
            self.handler.write_file(self.path, self.string)
        if self._phase == 'processing':
            self.prosessor(*args, **kwargs)
        outputs  = {
                    f'{self._phase}_path': self.path,
                    f'{self._phase}_file_exists': self.file_exists,
                    'work_file_name': self.work_file_name,
                    f'{self._phase}_string': self.string,
                    f'string': self.string,
        }
        logprint(f"{outputs = }", level='info')
        return outputs

    def parse_source(self, *args, **kwargs) -> None:
        if self.update_source_type == 'file':
            self.string = self.handler.load_file(*args, **kwargs)
        elif self.update_source_type == 'string':        
            if self._phase == 'json':
                self.data = JsonParser(*args, text=self.string, **kwargs)()
            elif self._phase in {'integration', 'processing'}:
                self.data = MdParser(*args, md_string=self.string, **kwargs)(*args, **kwargs)
            elif self._phase == 'prompt':
                self.data = PromptEngine(*args, **kwargs)(*args, **kwargs)
            self.string = self.data.get(sts.content_key)
        self.work_file_name = self.data.get(sts.target_key)

    def veryfy_source(self, *args, path:str, string:str, update_source:str, 
        update_source_type:str, file_exists:bool, **kwargs):
        assert not ((string and update_source) and (update_source_type != 'file')), \
        logprint(f"Ambigous sources \n{string = }\n{update_source = }", level='error')
        # source = string or update_source
        if update_source_type == 'string' or not update_source_type:
            self.update_source_type = 'string'
            self.string = string or update_source
        elif path and file_exists:
            assert os.path.exists(path), \
            logprint(f"{self._phase = } File not found {path = }", level='error')
            self.update_source_type = 'file'
            self.path = path
            self.file_exists = file_exists
        elif string and self._phase == 'prompt':
            self.string = string
            self.update_source_type = 'string'
        else:
            logprint(f"{self._phase = } Source not found !", level='error')


class FileHandler:

    def __init__(self, phase, *args, **kwargs):
        self._phase:str = phase

    def load_file(self, path, *args, **kwargs) -> None:
        assert self._phase in path, logprint(f"Not a {self._phase} path!", level='error')
        with open(path, "r", encoding="utf-8") as f:
            string = f.read()
        return string

    def write_file(self, path, content, *args, **kwargs) -> None:
        """Writes the parsed JSON string to the CR path."""
        logprint(f"writing file {path = }\n{content[:100] = }", level='info')
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return sts.file_exists_default

    def _create_restore_file(self, *args, soruce_path:str, restore_path:str, **kwargs):
        shutil.copyfile(source_path, restore_path)
        logprint(f"creating restore file: {restore_path}", level='info')

    def remove_file(self, path, *args, **kwargs) -> None:
        """Deletes the CR file at the specified path."""
        if os.path.exists(path):
            os.remove(path)
            logprint(f"removing file: {path}", level='warning')

    def remove_operation(self, *args, hot:bool=False, path:str, **kwargs):
        self.write_file(path, *args, **kwargs)
        if hot:
            self._create_restore_file(*args, **kwargs)
            self.remove_file(*args, **kwargs)

    def write_operation(self, *args, hot:bool=False, source_path:str, path:str, 
        **kwargs):
        # in any case we write to the processing path for CR documentation
        self.write_file(path, *args, **kwargs)
        if hot:
            self._create_restore_file(*args, source_path=source_path, **kwargs)
            self.write_file(source_path, *args, **kwargs)

    def get_path(self, wfn, *args, pg_name: str, cr_id: str, **kwargs) -> tuple[str, str]:
        """Derives the full CR JSON file path and the target filename."""
        _dir = getattr(sts, f"{self._phase}_dir")(pg_name)
        _file_name = getattr(sts, f"{self._phase}_file_name")(wfn, cr_id)
        return os.path.join(_dir, _file_name)


class ProcessEngine:


    def __init__(self, *args, **kwargs):
        self.csts = CSTSource(*args, **kwargs)
        self.cstd = CSTDelta(*args, **kwargs)
        self.F = Validator_Formatter()
        self.handler = FileHandler(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        """
        WHY: Honor package-level 'remove' with same hot+archive flow as _write_output.
        """
        self.process_python(*args, **kwargs)
        self.process_operations(*args, **kwargs)
        return self

    def process_python(self, *args, source_path:str, integration_path:str, **kwargs):
        assert source_path and integration_path, logprint(
            f"Missing processing input {source_path = }, {integration_path = }", level='error')
        if not str(integration_path).endswith('.py'):
            return
        self.csts(*args, source_path=source_path, **kwargs)
        self.cstd(*args, source_path=integration_path, **kwargs)
        self.pg_head, self.cr_ops = self.cstd.body
        self.marker = self.pg_head.create_marker(*args, **kwargs)
        self.pg_op = self.pg_head.cr_op

    def process_operations(self, *args, source_path:str, **kwargs):
        if self.pg_head.cr_op == 'remove':
            # when hot is False removal is simulated by outcommenting the source file content
            self.handler.remove_operation((
                                f"{self.marker}\n\n"
                                f"\"\"\"\n"
                                f"{self.handler.load_file(source_path, *args, **kwargs)}"
                                f"\n\"\"\"\n"
                                ), source_path, *args, **kwargs)
        elif self.pg_head.cr_op == 'update':
            tf = Transformer(self.csts.body, self.cstd.body, *args, **kwargs)(*args, **kwargs)
            transformed = self.F(tf.source.code, *args, **kwargs)
            self.handler.write_operation(transformed, *args, source_path=source_path, **kwargs)
        elif self.pg_head.cr_op == 'create':
            # NOTE: For 'create', we use the entire content of the integration file
            # excluding the package header, which is available in CSTD's source_text.
            # We must remove the package header line from the raw text.
            raw_code = re.sub(sts.pg_header_regex, '', self.cstd.source_text, 1).strip()
            transformed = self.F(raw_code, *args, **kwargs)
            self.handler.write_operation(transformed, *args, source_path=source_path, **kwargs)


class PromptEngine:


    def __init__(self, *args, prompt_file_exists:bool=False, **kwargs):
        self.prompt = None
        self.path = None
        self.content = None
        self.file_exists = prompt_file_exists

    #-- cr_op: replace, cr_type: function, cr_anc: prompt, cr_id: 2025-10-14-19-59-41 --#
    def __call__(self, *args, **kwargs) -> None:
        # printing.pretty_dict('kwargs', kwargs)
        self.prompt = self.mk_prompt(*args, **kwargs)
        self.content = self.model_create_cr(*args, **kwargs)
        self.data = self.prep_data(*args, **kwargs)
        return self.data

    def prep_data(self, *args, work_file_name:str, **kwargs) -> dict:
        return {
                sts.target_key: work_file_name,
                sts.content_key: self.content,
                }

    def mk_prompt(self, *args, api, **kwargs) -> str:
        pg_context = self.get_pg_context(*args, **kwargs)
        # main prompt construction
        guidelines = self.insert_guidelines(*args, **kwargs)
        class_names = collections.class_names_from_file(*args, **kwargs)
        prompt = self.mk_instructions(*args,
                                            pg_context=pg_context,
                                            guidelines=guidelines,
                                            class_names=class_names,
                    **kwargs)
        logprint(f"Prompt", level='dev')
        print(printing.pretty_prompt(prompt, *args, **kwargs))
        return printing.clean_pipe_text(prompt)

    def get_pg_context(self, *args, string:str=None, integration_format:str='md', 
        **kwargs) -> str:
        # first model call to get base prompt with context
        pl = PromptEngine.mk_payload(*args, 
                                            api='prompt', 
                                            string='codeon context', 
                                            verbose=2,
                                            **kwargs)
        r = PromptEngine.model_call(pl, *args, **kwargs).strip()
        # we cut intro and instructions from the resulting prompt to do our own
        prompt = r.split(sts.from_split, 1)[-1].rsplit(sts.to_split)[0]
        prompt = sts.from_split + prompt
        if integration_format == "md":
            # json instructions are not relevant if .md file so we cut it
            prompt = prompt.split(sts.readme_split)[0]
        return prompt

    def mk_instructions(self, *args, **kwargs) -> str:
        with open(sts.integration_file_templ_path, "r", encoding="utf-8") as f:
            templ = f.read()
        return '\n' + f"{self.render(templ, *args, **kwargs)}".strip() + '\n'

    @staticmethod
    def mk_payload(*args, api='prompt', string:str, work_dir:str, work_file_name:str, 
        verbose:int=0, external_prompt:str=None, **kwargs):
        checks = {'api': api, 'string': string, 'work_dir': work_dir, 
                    'work_file_name': work_file_name}
        assert all(checks.values()), logprint(f"missing: {checks = }", level='error')
        assert not any([s in string for s in sts.jinja_seps]), \
        logprint(f"invalid chars inside jinja2 template: {sts.jinja_seps = }", level='error')
        return {
                    "api": api, 
                    "work_dir": work_dir,
                    "user_prompt": string if not external_prompt else None,
                    "external_prompt": external_prompt,
                    "work_file_name": work_file_name,
                    "kwargs_defaults": 'codeon',
                    "verbose": verbose,
                    }


    def insert_guidelines(self, *args, verbose:int=0, **kwargs) -> str:
        if verbose >= 2:
            with open(sts.cq_ex_llm_file, "r", encoding="utf-8") as cq:
                guidelines = cq.read()
        else:
            guidelines = "Apply: CQ:EX-LLM (PEP) to write professional python."
        return '\n' + guidelines.strip() + '\n'

    def render(self, text, *args, **kwargs) -> str:
        """jinja2 renders a text using kwargs as context"""
        assert kwargs, "PromptEngine.render: kwargs must not be empty."
        pr_fields = set(re.findall(r'{{\s*(\w+)\s*}}', text))
        context = {f: kwargs.get(f) for f in pr_fields}
        ctx = '\n'.join([f"{k}:\t{str(v)[:50]}" for k, v in context.items()])
        assert (pr_fields == context.keys()) and all(context.values()), \
            logprint((  f"missing fields in kwargs:"
                        f"\n{pr_fields = }"
                        f"\ncontext:\n{ctx}"), level='error')
        return jinja2.Template(text).render(context) + '\n'

    def model_create_cr(self, *args, api, **kwargs) -> str:
        payload = self.mk_payload(*args, api='thought', external_prompt=self.prompt, **kwargs)
        r = self.model_call(payload, *args, **kwargs)
        return self.prompt + '\n\n' + r

    @staticmethod
    def model_call(payload, *args, **kwargs):
        # this calls altered bytes server on localhost
        printing.pretty_dict('PromptEngine.model_call.payload', payload, color=Fore.YELLOW)
        r = str(requests.post(  f"{getattr(sts, 'model_ip', 'http://localhost')}:"
                                f"{getattr(sts, 'model_default_port', 9005)}/call/",
                                    json={**payload},
                                    headers={"Accept": "application/json"}, 
                                    timeout=60,
                            )
                            .json()
                            .get("response")
                )
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
