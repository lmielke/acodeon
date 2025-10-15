# User Readme for Acodeon package

## Acodeon Description
Acodeon is an automated CR (change request) integration engine using the Python `libcst` library. 
It is designed to allow LLMs to create and maintain codebases by using an automated,
modularized (methods, classes, etc.) integration mechanism. 
The updates are provided as full modules, classes, methods, or imports using a `__cr_integration_file__`.

## Installation Instructions
Currently Acodeon is available as a GitHub repo. To install it, clone the repo and install the dependencies using Pipenv.

```powershell
git clone ...
cd acodeon
pipenv install
```

## How to run codeon
```shell
codeon create -s 'json_string' [ --hard ] [ -b ]
codeon update -s target_file_name.py [ --hard ] [ -b ]
codeon prompt_info -s target_file_name -i package -v 2
codeon code -s target_file_name.py -p '__CR Prompt__ text or file name' [--hard] [ -b ]
```

## How it Works
- codeon uses APIs to integrate change-requests into the target file
- The integrated target files are saved to `~/.codeon/cr_logs/package_name/...` unless the `--hard` flag is used.
- <span style="color:red; font-weight:bold;">STRONG NOTICE: The `--hard=True` flag creates, updates, or removes the target file directly!</span>
- The `-b=True` flag runs the `black` formatter on the updated file.

## Available APIs
- **create:** creates a new target file from a `__cr_integration_file__`
- **update:** updates an existing target file from a change-request file
- **prompt_info:** generates the prompt context for the target package to be send to the LLM
- **code:** integrates all prior steps: generates the prompt, calls the LLM, creates/updates the target file


Each file must begin with a **package cr-header** defining the operation (create, update).  
Each code block in the file has its own **unit cr-header** (insert_before, insert_after, replace, remove).

## What are cr-headers?
CR headers are commented instruction lines inside the `__cr_integration_file__` that tell the Acodeon APIs
how to modify the target file.

### Types of cr-headers
#### Package cr-header (mandatory)
Indicates the file-level operation to perform:
```python
#--- cr_op: create, cr_type: file, cr_anc: test_parsers_data.py ---#
```

#### Unit cr-header
Indicates the operation on a specific code object:
```python
#-- cr_op: insert_after, cr_type: import, cr_anc: import time, install: False --#
```

### Common cr-header fields
- **cr_op:** operation (create, update, insert_after, insert_before, replace, remove)
- **cr_type:** object type (file, import, class, method, etc.)
- **cr_anc:** the spatial anchor (target or insertion point)
- **install:** optional bool; whether a dependency install is required

## Creating a change-request
The process consists of four steps:

1. A user writes a **CR Prompt** describing desired code changes (with `prompt_info`).
2. The LLM generates a **__cr_integration_file__** and delivers it as a JSON string.
3. codeon processes the JSON to create the `__cr_integration_file__`.
4. codeon then applies it to create/update/remove the target file according to CQ:EX-LLM standards.
**CQ:EX-LLM** = Code Quality Excellence — concise, deterministic, professional Python generation.

---

## Worked Example (headers.py)

### Start state (reduced)
```python
from dataclasses import asdict, dataclass
from enum import Enum
import yaml

@dataclass
class CR_OBJ_FIELDS:
    CR_OP: str = 'cr_op'
    CR_TYPE: str = 'cr_type'
    CR_ANC: str = 'cr_anc'
    INSTALL: str = 'install'

class OP_M(str, Enum):
    IB, IA, RP, RM = 'insert_before', 'insert_after', 'replace', 'remove'

class CRTypes(str, Enum):
    IMPORT, METHOD, FUNCTION, CLASS, FILE = (
        'import', 'method', 'function', 'class', 'file'
    )

class CrHeads:
    def __init__(self, *args, **kwargs):
        for _, v in asdict(CR_OBJ_FIELDS()).items():
            setattr(self, v, None)
        self.start_token, self.end_token = '#-- ', ' --#'
        self._enum_map = {'cr_op': OP_M, 'cr_type': CRTypes}

    def load_string(self, *args, head: str, **kwargs):
        s = head[len(self.start_token):-len(self.end_token)].strip()
        d = yaml.safe_load('\n'.join(p.strip() for p in s.split(','))) or {}
        for k, v in d.items():
            em = self._enum_map.get(k)
            setattr(self, k, em(v) if em else v)

class UnitCrHeads(CrHeads):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
```

### CR Prompt example (__cr_prompt_)
Below is an example of a CR prompt that would generate the desired changes.
```markdown
Please update headers.py:
- Add PackageCrHeads using '#--- ' … ' ---#' tokens and print a green message when a package header loads.
- Add CrHeads.create_marker(cr_id: str|None) -> str to render headers.
- Replace CrHeads.load_string with a stricter version that asserts dict shape.
- Remove the private coercion helper.
- Insert colorama import via an insert_after on "import os".
- Keep methods short and deterministic.
NOTE: CQ:EX-LLM to generate professional Python.
```

### Target State
The resulting updated `headers.py` will contain all requested changes, each clearly marked with its respective CR headers.
Example markers:

```python
#-- cr_op: insert_after, cr_type: import, cr_anc: import os, install: False, cr_id: 2025-10-09-12-32-22 --#
#-- cr_op: replace, cr_type: method, class_name: CrHeads, cr_anc: load_string, cr_id: 2025-10-09-12-32-22 --#
```

### __cr_integration_file__
```python
#--- cr_op: update, cr_type: file, cr_anc: headers.py ---#

#-- cr_op: insert_after, cr_type: import, cr_anc: import os, install: False --#
from colorama import Fore, Style

#-- cr_op: replace, cr_type: method, class_name: CrHeads, cr_anc: load_string --#
def load_string(self, *args, head: str, **kwargs):
    s = head[len(self.start_token):-len(self.end_token)].strip()
    d = yaml.safe_load('\n'.join(p.strip() for p in s.split(',')))
    assert isinstance(d, dict), 'Parsed cr-header is not a dict.'
    for k, v in d.items():
        em = self._enum_map.get(k)
        setattr(self, k, em(v) if em else v)

#-- cr_op: remove, cr_type: method, class_name: CrHeads, cr_anc: _coerce --#

#-- cr_op: insert_after, cr_type: method, cr_anc: CrHeads.__init__ --#
def create_marker(self, *args, cr_id: str | None = None, **kwargs) -> str:
    keys = ('cr_op', 'cr_type', 'cr_anc', 'install')
    data = {k: getattr(self, k) for k in keys if getattr(self, k, None) is not None}
    if cr_id:
        data['cr_id'] = cr_id
    parts = [f'{k}: {getattr(v, 'value', v)}' for k, v in data.items()]
    return f'{self.start_token}{', '.join(parts)}{self.end_token}'

#-- cr_op: insert_after, cr_type: class, cr_anc: CrHeads --#
class PackageCrHeads(CrHeads):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_token, self.end_token = '#--- ', ' ---#'

    def __call__(self, *args, head: str, **kwargs):
        self.load_string(head=head)
        print(f"{Fore.GREEN}Loaded package cr-header{Style.RESET_ALL}")
```

### __cr_integration_json__

```json
{
  "target": "headers.py",
  "content": "#--- cr_op: update, cr_type: file, cr_anc: headers.py ---#\n#-- cr_op: insert_after, cr_type: import, cr_anc: import os, install: False --#\nfrom colorama import Fore, Style\n\n#-- cr_op: replace, cr_type: method, class_name: CrHeads, cr_anc: load_string --#\ndef load_string(self, *args, head: str, **kwargs):\n    '''Strict parse to avoid silent drift.'''\n    s = head[len(self.start_token):-len(self.end_token)].strip()\n    d = yaml.safe_load('\\n'.join(p.strip() for p in s.split(',')))\n    assert isinstance(d, dict), 'Parsed cr-header is not a dict.'\n    for k, v in d.items():\n        em = self._enum_map.get(k)\n        setattr(self, k, em(v) if em else v)\n\n#-- cr_op: remove, cr_type: method, class_name: CrHeads, cr_anc: _coerce --#\n\n#-- cr_op: insert_after, cr_type: method, cr_anc: CrHeads.__init__ --#\ndef create_marker(self, *args, cr_id: str|None=None, **kwargs) -> str:\n    '''Render normalized header for traceable diffs.'''\n    keys = ('cr_op','cr_type','cr_anc','install')\n    data = {k: getattr(self,k) for k in keys if getattr(self,k,None) is not None}\n    if cr_id: data['cr_id'] = cr_id\n    parts = [f\"{k}: {getattr(v,'value',v)}\" for k,v in data.items()]\n    return f\"{self.start_token}{', '.join(parts)}{self.end_token}\"\n\n#-- cr_op: insert_after, cr_type: class, cr_anc: CrHeads --#\nclass PackageCrHeads(CrHeads):\n    def __init__(self, *args, **kwargs):\n        super().__init__(*args, **kwargs)\n        self.start_token, self.end_token = '#--- ', ' ---#'\n    def __call__(self, *args, head: str, **kwargs):\n        self.load_string(head=head)\n        print(f\"{Fore.GREEN}Loaded package cr-header{Style.RESET_ALL}\")\n"
}

```
