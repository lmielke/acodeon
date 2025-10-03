#--- op_code: update, obj: file, target: test_parsers_data.py ---#
# package op-code pointing to file test_parsers_data.py
# C:\Users\lars\python_venvs\packages\acodeon\codeon\test\data\op_test_parsers_data.py


# module op-codes with changes to test_parsers_data.py
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
