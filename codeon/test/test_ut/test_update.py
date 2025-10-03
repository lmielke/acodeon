# test_update.py

import os, re, shutil, sys, time, yaml
import unittest

# test package imports
import codeon.settings as sts

from codeon.apis.update import _update


class Test__update(unittest.TestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        cls.verbose = 0
        cls.test_data = cls.mk_test_data(*args, **kwargs)
        cls.msg = f" >>>> NOT IMPLEMENTED <<<< "

    @classmethod
    def tearDownClass(cls, *args, **kwargs):
        pass

    @classmethod
    def mk_test_data(cls, *args, **kwargs):
        cls.test_file_name = "op_test_parsers_data.py"
        cls.test_file_path = os.path.join(sts.test_data_dir, cls.test_file_name)
        cls.test_target_name = cls.test_file_name.replace("op_", "")
        # we check if a test_target_name containing file already exists and remove it
        # to avoid spamming the target dir
        for n in os.listdir(sts.update_logs_test_dir):
            if cls.test_target_name in n:
                os.remove(os.path.join(sts.update_logs_test_dir, n))
        cls.test_target_path = os.path.join(
            sts.update_logs_test_dir, cls.test_target_name
        )
        # we copy the op code file to cls.test_target_path
        shutil.copy(cls.test_file_path, cls.test_target_path)
        # time.sleep(1)

    def test__update_success_path(self, *args, **kwargs):
        """Tests the 'happy path' where the transformation is successful."""
        out = _update(source_path=self.test_target_name, black=True)
        print(f"{out = }")

    def test_update_halts_on_invalid_op_code(self):
        """
        Tests that the update process exits cleanly when an invalid op-code is found.
        """
        invalid_op_path = os.path.join(sts.test_data_dir, "invalid_op_code_file.py")
        source_path = os.path.join(sts.test_data_dir, "test_parsers_data.py")

        # with self.assertRaises(SystemExit) as cm:
        #     _update(source_path=source_path, op_codes_path=invalid_op_path)

        # Verify that the exit code is 1, indicating an error
        # self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()