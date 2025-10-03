import os
import json
import unittest

import codeon.settings as sts
from codeon.apis import create
from codeon.helpers.file_info import UpdatePaths
import codeon.settings as sts


class Test__create(unittest.TestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        """Set up paths and load test data from file once for the class."""
        # Path to the source JSON file for the test
        cls.json_file_path = os.path.join(
            sts.test_data_dir, "op_test_create_parsers_data.json"
        )

        # Read the content of the JSON file into a string
        with open(cls.json_file_path, "r", encoding="utf-8") as f:
            cls.json_string_content = f.read()

        # Determine the expected output path from the JSON content
        paths = UpdatePaths(pg_name=sts.package_name)
        cls.op_code_dir = paths.op_code_dir
        data = json.loads(cls.json_string_content)
        cls.target_file_name = data["target"]
        cls.expected_path = os.path.join(sts.update_temp_test_dir, cls.target_file_name)

    def setUp(self):
        """Clean up the target file before each test."""
        if os.path.exists(self.expected_path):
            os.remove(self.expected_path)

    def tearDown(self):
        """Clean up the target file after each test."""
        # if os.path.exists(self.expected_path):
        #     os.remove(self.expected_path)
        pass

    def test_stage_op_code_file_from_json_string(self):
        """
        Tests that the create API correctly stages an op-code file
        from a JSON string that was read from a file.
        """
        self.assertFalse(os.path.exists(self.expected_path))

        # Run the create API, passing the JSON content as a string
        status_dict = create.main(json_string=self.json_string_content, hard=False)
        self.assertTrue(os.path.exists(self.expected_path))

        # Verify the content was written correctly
        expected_code = json.loads(self.json_string_content)["code"]
        with open(self.expected_path, "r") as f_staged:
            actual_code = f_staged.read()
        self.assertEqual(expected_code, actual_code)


if __name__ == "__main__":
    unittest.main()