# test_codeon.py
# C:\Users\lars\python_venvs\packages\acodeon\codeon\test\test_ut\test_codeon.py

import logging
import os
import unittest
import yaml

import codeon.codeon as codeon
from codeon.helpers.function_to_json import FunctionToJson
import codeon.settings as sts

class Test_DefaultClass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verbose = 0
        # we read the code of the codeon module
        cls.test_work_file_name = os.path.basename(codeon.__file__)
        cls.pars = {
                    'api': 'cr',
                    'infos': ['package'],
                    'prompt_string': "We need a new __repr__ method for the Codeon class.",
                    'source_path': cls.test_work_file_name,
                    'integration_format': 'md',
                    'verbose': 2,
                    'testing': False,
                    'yes': False,
                    }

    @classmethod
    def tearDownClass(cls):
        pass

    def test__call__(self):
        cr = codeon.Codeon(**self.pars)(**self.pars)
        print(f"{cr = }")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
