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

    def test__update_success_path(self, *args, **kwargs):
        """Tests the 'happy path' where the transformation is successful."""
        _update(source_path=self.test_target_name, black=True)

    def test_update_halts_on_invalid_op_code(self):
        """
        Tests that the update process exits cleanly when an invalid op-code is found.
        """
        invalid_op_path = os.path.join(sts.test_data_dir, "invalid_op_code_file.py")
        source_path = os.path.join(sts.test_data_dir, "test_parsers_data.py")

        with self.assertRaises(SystemExit) as cm:
            _update(source_path=source_path, op_codes_path=invalid_op_path)

        # Verify that the exit code is 1, indicating an error
        self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()