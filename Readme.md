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
# codeon uses the update api to apply the updates to the source file
# the updated file is saved to ~/.codeon/update_logs/ch_id_file_name.py unless the --hard flag is used
# --hard updates the source file directly
# the -b flag will run black code formatter on the updated file
codeon update -s source_file.py --hard -b
```

## Creating a op update file
The update file is created by an LLM it uses op-codes to group the updates inside the file
in a execution/update order.
NOTE: Every code file must have a 'package op_code' near the top of the file, to be processed!

### Examples:

This is a example of a init file to be created (op_code: create). It is provided in order to be processed
by the 'create api'. The 'create api' will parse the op-codes and create the source file.
The init file must be the content of a valid properly formatted executable python .py file.


```python
"""
#--- op_code: create, obj: file, target: test_parsers_data.py ---#
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
        return "after"


class SecondClass:
    """Tests 'insert_before' and 'replace' operations."""

    def method_before_replace(self, *args, **kwargs):
        """This method should remain before the inserted/replaced method."""
        return "before"

    def method_to_replace(self, *args, **kwargs):
        """This method is the target for 'insert_before' and 'replace'."""
        return "This is the original method."

    def method_after_replace(self, *args, **kwargs):
        """This method should remain untouched after all operations."""
        return "after"


class ThirdClass:
    """Tests the 'remove' operation."""

    def method_before_remove(self, *args, **kwargs):
        """This method should remain after the removal."""
        return "before"

    def method_to_remove(self, *args, **kwargs):
        """This method is targeted for removal."""
        print("This method will be removed.")

    def method_after_remove(self, *args, **kwargs):
        """This method should remain after the removal."""
        return "after"
```

This is a example of a 'update' file with all the possible existing op-codes. It is provided
in order to be processed by the 'update api'. The 'update api' will parse the op-codes and
apply the changes to the source file.

```python
# MANDATORY: package op-code to indicate the operation and the file/module at hand
# NOTE: The package op-code starts with # 3 dashes like: #---
#--- op_code: update, obj: file, target: test_parsers_data.py ---#

# module op-codes with changes to the source code file
#-- op_code: insert_after, obj: import, target: import time, install: False --#
import re

#-- op_code: insert_after, obj: method, target: FirstClass.__init__ --#
def method_to_insert_after(self, *args, **kwargs) -> None:
    """Should be inserted after FirstClass.__init__."""
    print("Update method for insert_after logic.")

#-- op_code: insert_before, obj: method, target: SecondClass.method_to_replace --#
def method_to_insert_before(self, *args, code: str, verbose: int, **kwargs) -> bool:
    """Should be inserted before SecondClass.method_to_replace."""
    print("Update method for insert_before logic.")

#-- op_code: insert_before, obj: method, target: SecondClass.method_to_replace --#
def another_method_to_insert_before(self, *args, **kwargs) -> None:
    """Another placeholder for a future insertion method."""
    print("Another update method for insert_before logic.")

#-- op_code: replace, obj: method, target: SecondClass.method_to_replace --#
@staticmethod
def method_to_replace(*args, **kwargs):
    """A second method to demonstrate replaces."""
    return "replaced by op_test_parsers_data.py"

#-- op_code: remove, obj: method, target: ThirdClass.method_to_remove --#

#-- op_code: insert_after, obj: class, target: SecondClass --#
class InsertedClass:
    """A new class inserted after SecondClass to demonstrate class insertion."""

    def __init__(self, *args, **kwargs) -> str:
        """This method was inserted as part of the class insert."""
        self.was_inserted = True

    def another_method(self, *args, **kwargs) -> str:
        """This second method was inserted as part of the class insert."""
        return "This is another method from the newly inserted class."
```
