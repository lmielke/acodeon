"""
# C:/Users/lars/python_venvs/packages/acodeon/codeon/test/data/source.py
This file contains three python classes to be used by the update api.
The update api takes operation files like op_2025-09-25-00-00-00_source.py and updates this file.
The updated file is stored as source.py inside the sts.resources_dir/update_logs directory.
"""
import os

class FirstClass:
    """Tests 'insert_after'. The new method should appear between
    __init__ and method_after_init.
    """

    def __init__(self, *args, **kwargs):
        """Initializes the class. Target for 'insert_after'."""
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