"""
# C:/Users/lars/python_venvs/packages/acodeon/codeon/test/data/source.py
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