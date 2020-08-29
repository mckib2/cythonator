'''Tests on typedefs.'''

import unittest

from .utils import _code_runner

class TestTypedefs(unittest.TestCase):
    def test_int(self):
        td = _code_runner('typedef int myInt;').typedefs[0]
        self.assertEqual(td.name, 'myInt')
        self.assertEqual(td.type.name, 'int')

    def test_not_referenced(self):
        td = _code_runner('typedef int myInt;').typedefs[0]
        self.assertFalse(td.referenced)

    def test_is_referenced(self):
        td = _code_runner(
            'typedef int myInt; myInt myCoolVariable = 42;').typedefs[0]
        self.assertTrue(td.referenced)

    def test_modifiers(self):
        tds = _code_runner('\n'.join([
            'typedef int& myInt_ref;',
            'typedef int* myInt_star;',
            'typedef int *const myInt_star_const;',
            'typedef const int constMyInt;',
        ])).typedefs
        self.assertTrue(tds[0].type.is_ref)
        self.assertTrue(tds[1].type.is_ptr)
        self.assertTrue(tds[2].type.is_ptr)
        self.assertTrue(tds[2].type.is_const_ptr)
        self.assertTrue(tds[3].type.is_const)

    def test_chained(self):
        td = _code_runner(
            'typedef int myInt; '
            'typedef myInt otherInt; '
            'typedef otherInt distantInt;').typedefs
        self.assertEqual(td[0].type.name, 'int')
        self.assertEqual(td[1].type.name, 'myInt')
        self.assertEqual(td[2].type.name, 'otherInt')
