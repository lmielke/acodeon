import os
import json
import unittest

import codeon.settings as sts
from codeon.apis import create
import codeon.settings as sts


class Test__create(unittest.TestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        """Set up paths and load test data from file once for the class."""
        # Path to the source JSON file for the test
        cls.json_file_path = os.path.join(sts.test_data_dir, "cr_test_parsers_data.json")
        cls.source_path = os.path.join(sts.test_data_dir, "test_parsers_data.py")
        cls.json_string_content, cls.code = cls.mk_json_from_code_file(cls.source_path, cls.json_file_path)
        cls.cr_id = sts.time_stamp()
        cls.expected_path = os.path.join(   sts.cr_stages_dir(sts.package_name), 
                                            f"cr_{cls.cr_id}_test_parsers_data.py")

    @classmethod
    def mk_json_from_code_file(cls, source_path: str, json_file_path: str) -> str:
        """
        Takes a source code file path and a target file name, and creates a json file from it 
        in the test data directory.
        Example:
        {
            "target": "example.py",
            "code": "print('Hello, World!')"
        }
        """
        code, target = '', ''
        if os.path.isfile(source_path):
            with open(source_path, "r", encoding="utf-8") as f:
                code = f.read()
            target = os.path.basename(json_file_path).replace("cr_", "")
        cr_op = "#--- cr_op: create, cr_type: file, cr_anc: test_parsers_data.py ---#"
        # we add the create cr_op at the start of the code if not already present
        if not '#--- cr_op: create' in code:
            code = f'{cr_op}\n{code}'
        json_data = {
                        'target': target,
                        'code': code
        }
        with open(json_file_path, "w", encoding="utf-8") as f_json:
            json.dump(json_data, f_json, indent=4)
        return json.dumps(json_data), code

    def setUp(self):
        """Clean up the target file before each test."""
        if os.path.exists(self.expected_path):
            os.remove(self.expected_path)

    def tearDown(self):
        """Clean up the target file after each test."""
        # if os.path.exists(self.expected_path):
        #     os.remove(self.expected_path)
        pass

    def test_stage_cr_cr_file_from_json_string(self):
        """
        Tests that the create API correctly stages an cr_integration_file
        from a JSON string that was read from a file.
        """
        self.assertFalse(os.path.exists(self.expected_path))

        # Run the create API, passing the JSON code as a string
        # d_path = r"C:\Users\lars\python_venvs\packages\acodeon\codeon\test\data\#cr_test_create_parsers_data.json"
        # with open(d_path, "r", encoding="utf-8") as f_json:
        #     test_json = f_json.read()
        # print(f"{self.json_string_content = }")
        status_dict = create.main(
                                        json_string=self.json_string_content, 
                                        api='create', 
                                        hot=False, 
                                        cr_id=self.cr_id,
                                        verbose=3,
                                        )
        self.assertTrue(os.path.exists(self.expected_path))

        # Verify the code was written correctly
        expected_code = json.loads(self.json_string_content)["code"]
        self.assertEqual(expected_code, self.code)


if __name__ == "__main__":
    unittest.main()