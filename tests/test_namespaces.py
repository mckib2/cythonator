'''Tests on functions.'''

import unittest

from .utils import _code_runner

class TestFunctionsNoArgs(unittest.TestCase):
    def test_anonymous_namespace(self):
        ns =_code_runner('namespace { void fun(); }')
        self.assertEqual(len(ns.namespaces), 0)
        self.assertEqual(len(ns.functions), 0)
