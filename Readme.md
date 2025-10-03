# User Readme for Acodeon package

## Acodeon Description
Acodeon is a automated code updating tool using the pyhton libcst library. It is designed to allow LLMs to refactor and update their codebases efficiently. The updates are provided inside a python file

## Installation Instructions
Currently acodeon is available as a github repo. In order to install it, you will need to clone the repo and install the dependencies using pipenv.

```powershell
git clone ...
cd acodeon
pipenv install
```

## How to run codeon
```shell
codeon create -s 'json_string' [ --hard ] [ -b ]
codeon update -s source_file_name.py [ --hard ] [ -b ]
```

## Execution Description
- codeon uses apis to apply the updates to the source file
- The updated files are saved to ~/.codeon/update_logs/package_name/... unless the --hard flag is used.
- <span style="color:red; font-weight:bold;">STRONG NOTICE: The --hard = True flag updates/creates/removes the source file directly!</span>
- The -b = True flag will run black code formatter on the updated file

## Available APIs
- create: creates a new source file from an __'op-code'__ file
    - contains a single package __'op-code'__ as first line: create
    - contains the full source code to be created
    - code must be a valid python file ready to be tested

- update: updates an existing source file from an op-code file
    - contains the package __'op-code'__ as first line: update
    - contains all changes with respect to a single source file
    - contains multiple op-codes: insert_after, insert_before, replace, remove
    - every op-code is followed by a code snippet to be inserted/replaced
    - each snippet must be valid python (import, function, class, method) ready to be tested
    - the remove op-code comes without a code snippet

## What are op-codes?
Op-codes are instructions to the acodeon apis to perform a specific operation on a specific 
source file. The op-codes are provided in a python file, called __'op-code'__ file. 
There is two types of __'op-code'__:
- Mandatory package op-code: first line in the op-code file, indicates the operation to be performed on the specified source file (create, update)
- module op-codes: indicates the operation to be performed on a specific snippet of code (insert_after, insert_before, replace, remove)

## Creating a op-code file
The op-code file content is created by an LLM. It contains the delta coding together with its respective 
op-codes. The op-codes indicate the operation to be performed with the respective snippet, (i.e. insert, replace, remove)
NOTE: Every code file must have a 'package op_code' as first line of the file, to be processed!

### Examples:
This is a example of a new source file to be created (first line package_op_code: create). 
It is provided in order to be processed by the 'create api'. The 'create api' will parse 
the single op-code and create the source file.
The init file must be the content of a valid properly formatted executable python .py file.


```python
#--- op_code: create, obj: file, target: test_parsers_data.py ---#
"""
# MANDATORY: package op-code to indicate the operation and the file/module at hand
# NOTE: The package op-code starts with # 3 dashes like: #---
"""
import os
import time

class FirstClass:

    def __init__(self, *args, **kwargs):
        """Target for 'insert_after'."""
        pass

    def method_after_init(self, *args, **kwargs):
        """This method should remain after the inserted method."""
        return "method_to_insert_after was added before this method during update."


class SecondClass:
    """Tests 'insert_before' and 'replace' operations."""

    def method_before_replace(self, *args, **kwargs):
        """This method should remain before the inserted/replaced method."""
        return "This will stay the first method in the class."

    def method_to_replace(self, *args, **kwargs):
        """This method is the target for 'insert_before' and 'replace'."""
        return "This method must NOT be visible after update."

    def method_after_replace(self, *args, **kwargs):
        """This method should remain untouched after all operations."""
        return "This will stay the last method in the class."


class ThirdClass:
    """Tests the 'remove' operation."""

    def method_before_remove(self, *args, **kwargs):
        """This method should remain after the removal."""
        return "first method 1 of 2"

    def method_to_remove(self, *args, **kwargs):
        """This method is targeted for removal."""
        print("This method will be removed.")

    def method_after_remove(self, *args, **kwargs):
        """This method should remain after the removal."""
        return "last method, 2 of 2"
```

This is a example of a __'op-code'__ file with all currently available op-codes. It is provided
in order to be processed by the 'update api'. The 'update api' will parse the op-codes and
apply the changes to the source file.

```python
#--- op_code: update, obj: file, target: test_parsers_data.py ---#
# MANDATORY: package op-code is to indicate the operation and points to the file/module
# NOTE: The package op-code is the first line and starts with # 3 dashes like: #---

# module op-codes with changes to the source code
#-- op_code: insert_after, obj: import, target: import time, install: False --#
import re # this import will be inserted before the import time

#-- op_code: insert_after, obj: method, target: FirstClass.__init__ --#
def method_to_insert_after(self, *args, **kwargs) -> None:
    """Should be inserted after FirstClass.__init__."""
    print("This method was successfully inserted after __init__.")

#-- op_code: insert_before, obj: method, target: SecondClass.method_to_replace --#
def method_to_insert_before(self, *args, code: str, verbose: int, **kwargs) -> bool:
    """Should be inserted before SecondClass.method_to_replace."""
    print("This method was successfully inserted before method_to_replace.")

#-- op_code: insert_before, obj: method, target: SecondClass.method_to_replace --#
def another_method_to_insert_before(self, *args, **kwargs) -> None:
    """Another placeholder for a future insertion method."""
    print("This method was successfully inserted after method_to_insert_before.")

#-- op_code: replace, obj: method, target: SecondClass.method_to_replace --#
@staticmethod
def method_to_replace(*args, **kwargs):
    """A second method to demonstrate replaces."""
    return "original method was successfully replaced"

#-- op_code: remove, obj: method, target: ThirdClass.method_to_remove --#

#-- op_code: insert_after, obj: class, target: SecondClass --#
class InsertedClass:
    """A new class inserted after SecondClass to demonstrate class insertion."""

    def __init__(self, *args, **kwargs) -> str:
        """This method was inserted as part of the class insert."""
        self.was_inserted = True

    def another_method(self, *args, **kwargs) -> str:
        """This second method was inserted as part of the class insert."""
        return "This class was successfully inserted after SecondClass."

```

## op-code file serialization
The op-code content is delivered via the LLM api as a json.loads readable json object. The json object
contains two fields:
- source_file_name: the name of the source file to be created/updated
- content: the content of the op-code file as a string

### Example:
Below is an example of the json 
{
  "source_file_name": "test_create_parsers_data.py",
  "content": "\"\"\"\n#--- op_code: create, obj: file, target: test_parsers_data.py ---#\n# MANDATORY: package op-code to indicate the operation and the file/module at hand\n# NOTE: The package op-code starts with # 3 dashes like: #---\n\"\"\"\nimport os\nimport time\n\nclass FirstClass:\n\n    def __init__(self, *args, **kwargs):\n        \"\"\"Target for 'insert_after'.\"\"\"\n        pass\n\n    def method_after_init(self, *args, **kwargs):\n        \"\"\"This method should remain after the inserted method.\"\"\"\n        return \"after\"\n\n\nclass SecondClass:\n    \"\"\"Tests 'insert_before' and 'replace' operations.\"\"\"\n\n    def method_before_replace(self, *args, **kwargs):\n        \"\"\"This method should remain before the inserted/replaced method.\"\"\"\n        return \"before\"\n\n    def method_to_replace(self, *args, **kwargs):\n        \"\"\"This method is the target for 'insert_before' and 'replace'.\"\"\"\n        return \"This is the original method.\"\n\n    def method_after_replace(self, *args, **kwargs):\n        \"\"\"This method should remain untouched after all operations.\"\"\"\n        return \"after\"\n\n\nclass ThirdClass:\n    \"\"\"Tests the 'remove' operation.\"\"\"\n\n    def method_before_remove(self, *args, **kwargs):\n        \"\"\"This method should remain after the removal.\"\"\"\n        return \"before\"\n\n    def method_to_remove(self, *args, **kwargs):\n        \"\"\"This method is targeted for removal.\"\"\"\n        print(\"This method will be removed.\")\n\n    def method_after_remove(self, *args, **kwargs):\n        \"\"\"This method should remain after the removal.\"\"\"\n        return \"after\"\n"
}