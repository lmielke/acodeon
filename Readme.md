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
codeon update -s work_file_name.py [ --hard ] [ -b ]
codeon prompt_info -s work_file_name -i package -v 2
codeon code -s work_file_name.py -p '__CR Prompt__ text or file name' [--hard] [ -b ]
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

## What are cr-headers?
In order to implement CRs the update engine must know the location of the target files/modules and target code objects. Also the kind of operation perfomed on the target file must be provided. CR headers are commented instruction lines inside the `__cr_integration_file__` that tell the integration engine
how to modify the target file by providing both the target file/module name as well as the target code objects and operations to perform.

#### Package cr-header (mandatory)
The target module/file must ALLWAYS be declared to perform create or update operations.
```python
#--- cr_op: create, cr_type: file, cr_anc: test_parsers_data.py ---#
# module/file content ...
```

#### Unit cr-header
Inside the target module/file each targeted code block must be declared to guide the engines operations.
```python
#-- cr_op: insert_after, cr_type: import, cr_anc: import time, install: False --#
# code block content ...
```

### Valid cr-header fields
The update engine accepts the folloing fields in this specific order and format:
1. **cr_op:** operation to perform (create, update, insert_after, insert_before, replace, remove)
2. **cr_type:** object type (file, import, class, method, etc.)
3. **cr_anc:** anchor [class.method_name, class-name, import] to insert before/after, or replace/remove
4. **install:** optional bool; whether a dependency install is required
Note: Do not use other fields than the fields listed above!

### FAQ
Some header fields depend on others:
- cr_type: method -> cr_anc: ClassName.MethodName
- cr_type: class -> cr_anc: ClassName
- cr_type: import -> cr_anc: import statement

## Creating a change-request
1. A user writes a **CR Prompt** describing desired code changes (with `prompt_info`).
2. The LLM generates a __cr_integration_file__ and delivers it directly or as a JSON string.
3. codeon processes the JSON to create the `__cr_integration_file__`.
4. codeon then applies it to create/update/remove the target file according to CQ:EX-LLM standards.
**CQ:EX-LLM** = Code Quality Excellence — concise, deterministic, professional Python generation.

## Example (example.py)
The following shows a illustrative EXAMPLE of a CR process applied to a imaginary `example.py` file. The updated module will contain all requested changes, each clearly marked with its respective CR headers.

### CR Example Target Module (reduced)
```python
from dataclasses import asdict, dataclass
import os
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
This is an illustrative example of a CR.
- Add PackageCrHeads using '#--- ' … ' ---#' tokens and print a green message when a package header loads.
- Add CrHeads.create_marker(cr_id: str|None) -> str to render headers.
- Replace CrHeads.load_string with a stricter version that asserts dict shape.
- Remove the private coercion helper.
- Insert colorama import via an insert_after on 'import os'.
- Keep methods short and deterministic.
NOTE: CQ:EX-LLM to generate professional Python.

Example markers:

```python
#-- cr_op: insert_after, cr_type: import, cr_anc: import os, install: False --#
#-- cr_op: replace, cr_type: method, cr_anc: CrHeads.load_string --#
```

### Example __cr_integration_file__
The module in this example contains multiple classes that can be modified. This example contains all modifications (delta) to one of the classes and adds a new class.

```python
# example.py shows how the cr_integration_file should be structured
#--- cr_op: update, cr_type: file, cr_anc: example.py ---#

# in this example, the colorama import must be inserted after "import os"
#-- cr_op: insert_after, cr_type: import, cr_anc: import os, install: False --#
from colorama import Fore, Style

# in this example, the existing load_string method is replaced with the new version
#-- cr_op: replace, cr_type: method, cr_anc: CrHeads.load_string --#
def load_string(self, *args, head: str, **kwargs):
    s = head[len(self.start_token):-len(self.end_token)].strip()
    d = yaml.safe_load('\n'.join(p.strip() for p in s.split(',')))
    assert isinstance(d, dict), 'Parsed cr-header is not a dict.'
    for k, v in d.items():
        em = self._enum_map.get(k)
        setattr(self, k, em(v) if em else v)

#-- cr_op: remove, cr_type: method, cr_anc: CrHeads._coerce --#

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


### Example __cr_integration_json__

```json
{
  "target": "example.py",
  "content": "#--- cr_op: update, cr_type: file, cr_anc: example.py ---#\n#-- cr_op: insert_after, cr_type: import, cr_anc: import os, install: False --#\nfrom colorama import Fore, Style\n\n#-- cr_op: replace, cr_type: method, class_name: CrHeads, cr_anc: load_string --#\ndef load_string(self, *args, head: str, **kwargs):\n    '''Strict parse to avoid silent drift.'''\n    s = head[len(self.start_token):-len(self.end_token)].strip()\n    d = yaml.safe_load('\\n'.join(p.strip() for p in s.split(',')))\n    assert isinstance(d, dict), 'Parsed cr-header is not a dict.'\n    for k, v in d.items():\n        em = self._enum_map.get(k)\n        setattr(self, k, em(v) if em else v)\n\n#-- cr_op: remove, cr_type: method, class_name: CrHeads, cr_anc: _coerce --#\n\n#-- cr_op: insert_after, cr_type: method, cr_anc: CrHeads.__init__ --#\ndef create_marker(self, *args, cr_id: str|None=None, **kwargs) -> str:\n    '''Render normalized header for traceable diffs.'''\n    keys = ('cr_op','cr_type','cr_anc','install')\n    data = {k: getattr(self,k) for k in keys if getattr(self,k,None) is not None}\n    if cr_id: data['cr_id'] = cr_id\n    parts = [f\"{k}: {getattr(v,'value',v)}\" for k,v in data.items()]\n    return f\"{self.start_token}{', '.join(parts)}{self.end_token}\"\n\n#-- cr_op: insert_after, cr_type: class, cr_anc: CrHeads --#\nclass PackageCrHeads(CrHeads):\n    def __init__(self, *args, **kwargs):\n        super().__init__(*args, **kwargs)\n        self.start_token, self.end_token = '#--- ', ' ---#'\n    def __call__(self, *args, head: str, **kwargs):\n        self.load_string(head=head)\n        print(f\"{Fore.GREEN}Loaded package cr-header{Style.RESET_ALL}\")\n"
}

```
