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

## How to run Acodeon
```shell
# codeon uses the update api to apply the updates to the source file
# the updated file is saved to ~/.codeon/update_logs/ch_id_file_name.py unless the --hard flag is used
# --hard updates the source file directly
# the -b flag will run black code formatter on the updated file
codeon update -s source_file.py -u "op_source_file.py" --hard -b
```

## Creating a op update file
The update file is created by an LLM it uses op-codes to group the updates inside the file
in a execution/update order.

Example:
```python
# op_2025-09-25-00-00-00_source.py
# This file contains op-codes (operations) to modify the source_file.py script.

#-- op: insert_after, target: FirstClass.__init__ --#
def method_to_insert_after(self, *args, **kwargs) -> None:
    """A placeholder for a future insertion method."""
    if self.verbose >= 2:
        print("insert_after result.")

#-- op: insert_before, target: SecondClass.method_to_replace --#
def method_to_insert_before(self, *args, code: str, verbose: int, **kwargs) -> bool:
    """Runs all validation steps."""
    if verbose >= 2:
        print("insert_before result")
    return True

#-- op: replace, target: SecondClass.method_to_replace --#
@staticmethod
def method_to_replace(*args, **kwargs):
    """A second method to demonstrate replaces."""
    return "replaced by op_2025-09-25-00-00-00_source.py"

#-- op: remove, target: ThirdClass.method_to_remove --#
```
