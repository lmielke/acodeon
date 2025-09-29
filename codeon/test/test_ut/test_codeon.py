# test_codeon.py
# C:\Users\lars\python_venvs\packages\acodeon\codeon\test\test_ut\test_codeon.py

import logging
import os
import unittest
import yaml

from codeon.codeon import DefaultClass
from codeon.helpers.function_to_json import FunctionToJson
import codeon.settings as sts

class Test_DefaultClass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verbose = 0

    @classmethod
    def tearDownClass(cls):
        pass

    @FunctionToJson(schemas={"openai"}, write=True)
    def test___str__(self):
        pc = DefaultClass(pr_name="acodeon", pg_name="codeon", py_version="3.7")
        expected = "DefaultClass: self.pg_name = 'codeon'"
        self.assertEqual(str(pc), expected)
        logging.info("Info level log from the test")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
