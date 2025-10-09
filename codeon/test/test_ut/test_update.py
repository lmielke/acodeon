# test_update.py

import os, re, shutil, sys, time, yaml
import unittest

# test package imports
import codeon.settings as sts

import codeon.apis.update


class Test__update(unittest.TestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        cls.verbose = 0
        cls.test_data = cls.mk_test_data(*args, **kwargs)
        cls.json_file_path = os.path.join(sts.test_data_dir, "cr_headers.json" )
        cls.json_string_content = cls.get_json_str(*args, **kwargs)
        cls.msg = f" >>>> NOT IMPLEMENTED <<<< "

    @classmethod
    def tearDownClass(cls, *args, **kwargs):
        pass

    @classmethod
    def get_json_str(cls, *args, **kwargs):
        if os.path.isfile(cls.json_file_path):
            with open(cls.json_file_path, "r", encoding="utf-8") as f_json:
                json_str = f_json.read()
        return json_str

    @classmethod
    def mk_test_data(cls, *args, **kwargs):
        cls.test_file_name = "cr_test_parsers_data.py"
        cls.test_file_path = os.path.join(sts.test_data_dir, cls.test_file_name)
        # we remove cr_ from file which we need in test_data_dir to avoid name collisions
        cls.test_target_name = cls.test_file_name.replace("cr_", "")
        # we check if a test_target_name containing file already exists and remove it
        # to avoid spamming the target dir
        for n in os.listdir(sts.cr_integration_dir(sts.package_name)):
            if cls.test_target_name in n:
                os.remove(os.path.join(sts.cr_integration_dir(sts.package_name), n))
        cls.test_target_path = os.path.join(
            sts.cr_integration_dir(sts.package_name), cls.test_target_name
        )
        # we copy the op code file to cls.test_target_path
        shutil.copy(cls.test_file_path, cls.test_target_path)
        # time.sleep(1)

    def test__update_success_path(self, *args, **kwargs):
        """Tests the 'happy path' where the transformation is successful."""
        # out = codeon.apis.update.main(json_string=self.json_string_content, black=True, api='update')
        out = codeon.apis.update.main(source_path=self.test_target_name, black=True, api='update')
        print(f"{out = }")

    def test_update_halts_on_invalid_cr_op(self):
        """
        Tests that the update process exits cleanly when an invalid cr_integration_file is found.
        """
        invalid_cr_path = os.path.join(sts.test_data_dir, "invalid_cr_cr_file.py")
        source_path = os.path.join(sts.test_data_dir, "test_parsers_data.py")

        # with self.assertRaises(SystemExit) as cm:
        #     codeon.apis.update.main(source_path=source_path, cr_integration_path=invalid_cr_path)

        # Verify that the exit code is 1, indicating an error
        # self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()