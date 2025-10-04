#--- cr_op: update, cr_type: file, cr_anc: test_parsers_data.py ---#
# package cr_head pointing to file test_parsers_data.py
# C:\Users\lars\python_venvs\packages\acodeon\codeon\test\data\cr_test_parsers_data.py


# unit cr_head (s) with changes to test_parsers_data.py
#-- cr_op: insert_after, cr_type: import, cr_anc: import time, install: False --#
import re # this import will be inserted before the import time

#-- cr_op: insert_after, cr_type: method, cr_anc: FirstClass.__init__ --#
def method_to_insert_after(self, *args, **kwargs) -> None:
    """Should be inserted after FirstClass.__init__."""
    print("This method was successfully inserted after __init__.")

#-- cr_op: insert_before, cr_type: method, cr_anc: SecondClass.method_to_replace --#
def method_to_insert_before(self, *args, code: str, verbose: int, **kwargs) -> bool:
    """Should be inserted before SecondClass.method_to_replace."""
    print("This method was successfully inserted before method_to_replace.")

#-- cr_op: insert_before, cr_type: method, cr_anc: SecondClass.method_to_replace --#
def another_method_to_insert_before(self, *args, **kwargs) -> None:
    """Another placeholder for a future insertion method."""
    print("This method was successfully inserted after method_to_insert_before.")

#-- cr_op: replace, cr_type: method, cr_anc: SecondClass.method_to_replace --#
@staticmethod
def method_to_replace(*args, **kwargs):
    """A second method to demonstrate replaces."""
    return "original method was successfully replaced"

#-- cr_op: remove, cr_type: method, cr_anc: ThirdClass.method_to_remove --#

#-- cr_op: insert_after, cr_type: class, cr_anc: SecondClass --#
class InsertedClass:
    """A new class inserted after SecondClass to demonstrate class insertion."""

    def __init__(self, *args, **kwargs) -> str:
        """This method was inserted as part of the class insert."""
        self.was_inserted = True

    def another_method(self, *args, **kwargs) -> str:
        """This second method was inserted as part of the class insert."""
        return "This class was successfully inserted after SecondClass."
