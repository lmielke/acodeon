# test_prompt_info.py

import os, re, shutil, sys, time, yaml
import unittest

# test package imports
import codeon.settings as sts
import codeon.helpers.printing as hlpp

from codeon.apis.prompt_info import prompt_info

class Test_prompt_info(unittest.TestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        cls.verbose = 0
        cls.test_data = cls.mk_test_data(*args, **kwargs)
        cls.msg = f' >>>> NOT IMPLEMENTED <<<< '

    @classmethod
    def tearDownClass(cls, *args, **kwargs):
        pass

    @classmethod
    def mk_test_data(cls, *args, **kwargs):
        out = None
        # with open(os.path.join(sts.test_data_dir, "test_prompt_info.yml"), "r") as f:
        #     out = yaml.safe_load(f)
        return out


    def test_fmc(*args, **kwargs):
        

if __name__ == "__main__":
    unittest.main()
