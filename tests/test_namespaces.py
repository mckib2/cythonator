'''Tests on functions.'''

import unittest

from .utils import _code_runner


class TestFunctionsNoArgs(unittest.TestCase):
    def test_anonymous_namespace(self):
        ns = _code_runner('namespace { void fun(); }')
        self.assertEqual(len(ns.children), 0)

    def test_nested_namespace(self):
        global_ns = _code_runner([
            'namespace outer {',
            '    namespace inner {',
            '        void inner_fun();',
            '    }',
            '    void outer_fun();',
            '}',
        ])
        ns = global_ns.children[0]
        self.assertEqual(len(ns.children), 2)
        self.assertEqual(ns.children[0].name, 'outer::inner')
        self.assertEqual(ns.children[0].children[0].name, 'inner_fun')
        self.assertEqual(ns.children[1].name, 'outer_fun')

    def test_nested_anonymous_namespace(self):
        ns = _code_runner([
            'namespace {',
            '    namespace ns {',
            '        void invisible_func();',
            '    }',
            '}',
        ])
        self.assertEqual(len(ns.children), 0)
