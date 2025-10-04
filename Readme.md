# User Readme for Acodeon package

## Acodeon Description
Acodeon is a automated CR (change request) integration engine using the python libcst library. 
It is designed to allow LLMs to create and maintain codebases by using a automated integration
mechanism. The updates are provided inside using a cr_integration file.

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
- codeon uses apis to integrate change-requests to the target file
- The integrated target files are saved to ~/.codeon/cr_logs/package_name/... unless the --hard flag is used.
- <span style="color:red; font-weight:bold;">STRONG NOTICE: The --hard = True flag creates, updates or removes the target file directly!</span>
- The -b = True flag will run black code formatter on the updated file

## Available APIs
- create: creates a new target file from an __'cr-integration'__ file
    - which contains a single package __'cr-header'__ as first line: __create__
    - which for every cr_block contains the full module/file to be created.
    - the contained code must be a valid python file ready to be tested

- update: updates an existing target file from an change-request file
    - contains the single package __'cr-header'__ as first line: __update__
    - contains all changes with respect to a single target file or target module
    - contains multiple package cr-headers: insert_after, insert_before, replace, remove
    - every package cr-header is followed by a code snippet to be created or updated.
    - each snippet must be valid python (import, function, class, method) ready to be tested
    - a remove change-request comes without a code snippet, but only the package cr-header

## What are cr-headers?
CR header are commented instruction lines inside the __cr_integration_file__ that allow the acodeon apis
to perform necessary operations on the target file that integrate the requested changes. 

There is two types of __'cr-headers'__:
- Mandatory package cr-header: first line in the __cr_integration_file__, indicates the type of change-request
to be performed on the specified target file (create, update).
- module package cr: indicates the operation to be performed on a specific code object i.e. class or method ect. (insert_after, insert_before, replace, remove)

## Which cr-header fields are there?
- cr_op:str the operation to be performed (create, update, insert_after, insert_before, replace, remove)
- cr_type:str the type of code block/object the operation is performed on (file, import, class, method)
- cr_anchor:str the spacial target of the cr_op, (can be the target itself (replace, remove) or a spacial anchor point (insert_before, insert_after))
- install:bool (optional, default is False) indicates to the acodeon engine that a block requires installation of libraries and or dependencies.

## Creating a change-request
The change-request process consists of 4 sequential steps:
1. A change request is written by the customer. It describes the requested changes and contains the cr-context both in full and in relevant detail.
2. From the change-request a __cr_integration_file__ is created by a LLM and delivered in form of a json object.
3. Acodeon processes the json object to create the actual __cr_integration_file__.
4. The target file is then machine processed (created, updated or removed) based on the __cr_integration_file__. The target file contains the final updated code in acordance with the CR definitions and guidelines.

### Examples:
NOTE: to be processed properly every __cr_integration_file__ must have a specific machine readable structure with to the letter precision. 
The package cr-header as first line of its content!
This is a example of a crating __cr_integration_file__ (Note: first line package 'cr-header': create). 
It is provided in order to be processed by the 'create api'. The 'create api' will parse 
the single change-request and create the target file.
The init file must be a valid properly formatted executable python .py file.


```python
#--- cr_op: create, cr_type: file, cr_anchor: test_parsers_data.py ---#
"""
# MANDATORY: package change-request to indicate the operation and the file/module at hand
# NOTE: The package change-request starts with # 3 dashes like: #---
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

This is a example of a updating __cr_integration_file__ with all currently available unit cr-operations. It is provided
in order to be processed by the 'update api'. The 'update api' will parse the package cr-header (update) and then
sequentially apply the changes of all contained unit cr-headers (insert_before, insert_after, ...).

```python
#--- cr_op: update, cr_type: file, cr_anchor: test_parsers_data.py ---#
# MANDATORY: package change-request is to indicate the operation and points to the file/module
# NOTE: The package change-request is the first line and starts with # 3 dashes like: #---

# module package cr with changes to the source code
#-- cr_op: insert_after, cr_type: importcr_anchor: import time, install: False --#
import re # this import will be inserted before the import time

#-- cr_op: insert_after, cr_type: method, cr_anchor: FirstClass.__init__ --#
def method_to_insert_after(self, *args, **kwargs) -> None:
    """Should be inserted after FirstClass.__init__."""
    print("This method was successfully inserted after __init__.")

#-- cr_op: insert_before, cr_type: method, cr_anchor: SecondClass.method_to_replace --#
def method_to_insert_before(self, *args, code: str, verbose: int, **kwargs) -> bool:
    """Should be inserted before SecondClass.method_to_replace."""
    print("This method was successfully inserted before method_to_replace.")

#-- cr_op: insert_before, cr_type: method, cr_anchor: SecondClass.method_to_replace --#
def another_method_to_insert_before(self, *args, **kwargs) -> None:
    """Another placeholder for a future insertion method."""
    print("This method was successfully inserted after method_to_insert_before.")

#-- cr_op: replace, cr_type: method, cr_anchor: SecondClass.method_to_replace --#
@staticmethod
def method_to_replace(*args, **kwargs):
    """A second method to demonstrate replaces."""
    return "original method was successfully replaced"

#-- cr_op: remove, cr_type: method, cr_anchor: ThirdClass.method_to_remove --#

#-- cr_op: insert_after, cr_type: class,cr_anchort: SecondClass --#
class InsertedClass:
    """A new class inserted after SecondClass to demonstrate class insertion."""

    def __init__(self, *args, **kwargs) -> str:
        """This method was inserted as part of the class insert."""
        self.was_inserted = True

    def another_method(self, *args, **kwargs) -> str:
        """This second method was inserted as part of the class insert."""
        return "This class was successfully inserted after SecondClass."

```

## __cr_integration_file__ serialization
The __cr_integration_file__ content is delivered via the LLM api as a json.loads readable json object. The json object
contains two fields:
- __target__: the name of the target file to be created/updated or removed
- __content__: the content of the __cr_integration_file__ as a string

### Example:
Below is an example of the json-ified integration file. 
{
  "target": "test_create_parsers_data.py",
  "content": "\"\"\"\n#--- cr_op: create, cr_type: file, cr_anchor: test_parsers_data.py ---#\n# MANDATORY: package change-request to indicate the operation and the file/module at hand\n# NOTE: The package change-request starts with # 3 dashes like: #---\n\"\"\"\nimport os\nimport time\n\nclass FirstClass:\n\n    def __init__(self, *args, **kwargs):\n        \"\"\"Target for 'insert_after'.\"\"\"\n        pass\n\n    def method_after_init(self, *args, **kwargs):\n        \"\"\"This method should remain after the inserted method.\"\"\"\n        return \"after\"\n\n\nclass SecondClass:\n    \"\"\"Tests 'insert_before' and 'replace' operations.\"\"\"\n\n    def method_before_replace(self, *args, **kwargs):\n        \"\"\"This method should remain before the inserted/replaced method.\"\"\"\n        return \"before\"\n\n    def method_to_replace(self, *args, **kwargs):\n        \"\"\"This method is the target for 'insert_before' and 'replace'.\"\"\"\n        return \"This is the original method.\"\n\n    def method_after_replace(self, *args, **kwargs):\n        \"\"\"This method should remain untouched after all operations.\"\"\"\n        return \"after\"\n\n\nclass ThirdClass:\n    \"\"\"Tests the 'remove' operation.\"\"\"\n\n    def method_before_remove(self, *args, **kwargs):\n        \"\"\"This method should remain after the removal.\"\"\"\n        return \"before\"\n\n    def method_to_remove(self, *args, **kwargs):\n        \"\"\"This method is targeted for removal.\"\"\"\n        print(\"This method will be removed.\")\n\n    def method_after_remove(self, *args, **kwargs):\n        \"\"\"This method should remain after the removal.\"\"\"\n        return \"after\"\n"
}