"""
# C:/Users/lars/python_venvs/packages/acodeon/codeon/test/data/test_parsers_data.py
Source file for update api test.
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

    #-- cr_op: insert_after, cr_type: method, cr_anc: SecondClass.method_before_replace, cr_id: 2025-10-28-17-27-27 --#
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