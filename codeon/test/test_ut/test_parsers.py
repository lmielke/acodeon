# codeon/test/test_ut/test_parsers.py
import unittest
import os
import shutil

import libcst as cst

import codeon.settings as sts
from codeon.parsers import CSTSource, CSTDelta


class TestParsers(unittest.TestCase):
    """Unit tests for the CSTSource and CSTDelta parsers."""

    @classmethod
    def setUpClass(cls):
        """
        WHY: Prepare isolated temp copies of real test files using os.path
        to match codebase (no pathlib).
        """
        cls.test_dir = os.path.join(os.path.dirname(__file__), "temp_parser_test_data")
        if os.path.isdir(cls.test_dir):
            shutil.rmtree(cls.test_dir)
        os.makedirs(cls.test_dir, exist_ok=True)

        source_data_dir = sts.test_data_dir
        source_name = "test_parsers.py"
        original_source_file = os.path.join(source_data_dir, source_name)
        original_op_file = os.path.join(source_data_dir, f"op_2025-09-25-00-00-00_{source_name}" )

        cls.source_file = os.path.join(cls.test_dir, source_name)
        cls.op_file = os.path.join(cls.test_dir, f"op_2025-09-25-00-00-00_{source_name}")
        shutil.copy(original_source_file, cls.source_file)
        shutil.copy(original_op_file, cls.op_file)

    @classmethod
    def tearDownClass(cls):
        """WHY: Clean temp dir created in setUpClass."""
        shutil.rmtree(cls.test_dir)


    def test_cst_source_initialization_and_parsing(self):
        """WHY: Ensure CSTSource loads and parses into a cst.Module."""
        parser = CSTSource(source_path=self.source_file)
        self.assertIn("class FirstClass:", parser.source)
        tree = parser.parse()
        self.assertIsInstance(tree, cst.Module)


    def test_cst_delta_initialization_and_parsing(self):
        """WHY: Ensure CSTDelta loads and parses operations correctly."""
        parser = CSTDelta(op_codes_path=self.op_file)
        self.assertIn(
            "#-- op_code: remove, target: ThirdClass.method_to_remove", parser.source
        )

        operations = parser.parse()
        self.assertIsInstance(operations, list)
        self.assertEqual(len(operations), 4, "Should find all 4 operations in the file.")

        replace_op = operations[2]
        self.assertEqual(replace_op["op"], "replace")
        self.assertEqual(replace_op["class"], "SecondClass")
        self.assertEqual(replace_op["target"], "method_to_replace")
        self.assertIsInstance(replace_op["node"], cst.FunctionDef)
        self.assertTrue(hasattr(replace_op["node"], "decorators"))

        remove_op = operations[3]
        self.assertEqual(remove_op["op"], "remove")
        self.assertEqual(remove_op["class"], "ThirdClass")
        self.assertEqual(remove_op["target"], "method_to_remove")
        self.assertIsNone(remove_op["node"])


if __name__ == "__main__":
    unittest.main()

