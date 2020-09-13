'''Tests on typedefs.'''

import unittest

from .utils import _code_runner, _code_run_single_typedef


class TestTypedefs(unittest.TestCase):
    def test_int(self):
        td = _code_run_single_typedef('typedef int myInt;')
        self.assertEqual(td.name, 'myInt')
        self.assertEqual(td.type.name, 'int')

    def test_not_referenced(self):
        td = _code_run_single_typedef('typedef int myInt;')
        self.assertFalse(td.referenced)

    def test_is_referenced(self):
        td = _code_run_single_typedef(
            'typedef int myInt; myInt myCoolVariable = 42;')
        self.assertTrue(td.referenced)

    def test_modifiers(self):
        tds = _code_runner([
            'typedef int& myInt_ref;',
            'typedef int* myInt_star;',
            'typedef int *const myInt_star_const;',
            'typedef const int constMyInt;',
        ]).children
        self.assertTrue(tds[0].type.is_ref)
        self.assertTrue(tds[1].type.is_ptr)
        self.assertTrue(tds[2].type.is_ptr)
        self.assertTrue(tds[2].type.is_const_ptr)
        self.assertTrue(tds[3].type.is_const)

    def test_chained(self):
        td = _code_runner([
            'typedef int myInt;',
            'typedef myInt otherInt;',
            'typedef otherInt distantInt;',
        ]).children
        self.assertEqual(td[0].type.name, 'int')
        self.assertEqual(td[1].type.name, 'myInt')
        self.assertEqual(td[2].type.name, 'otherInt')

    def test_templated(self):
        td = _code_runner([
            'template<class U> class T {};',
            'typedef T<double * const>& Tdbl;'
        ]).children[1]
        self.assertEqual(td.type.name, 'T')
        self.assertFalse(td.type.is_ptr)
        self.assertTrue(td.type.is_ref)
        self.assertEqual(len(td.type.template_args), 1)
        self.assertEqual(td.type.template_args[0].name, 'double')
        self.assertTrue(td.type.template_args[0].is_const_ptr)
        self.assertFalse(td.type.template_args[0].is_ref)

    def test_recursive_templated(self):
        td = _code_runner([
            'template<class T, class U> class A {};',
            'template<class T, class U> class B {};',
            'typedef B<A<double *const, const long&>&, const int>& Tdbl;'
            # 'typedef A<double *const, const long&>& t1;',
            # 'typedef B<t1, const int>& Tdbl;',
        ]).children[-1]

        # the main type
        self.assertEqual(td.type.name, 'B')
        self.assertTrue(td.type.is_ref)
        self.assertFalse(td.type.is_ptr)
        self.assertFalse(td.type.is_const_ptr)
        self.assertFalse(td.type.is_const)

        # first template arg
        self.assertEqual(td.type.template_args[0].name, 'A')
        self.assertFalse(td.type.template_args[0].is_ptr)
        self.assertTrue(td.type.template_args[0].is_ref)
        self.assertFalse(td.type.template_args[0].is_const)

        # first template arg first template arg
        self.assertEqual(td.type.template_args[0].template_args[0].name, 'double')
        self.assertTrue(td.type.template_args[0].template_args[0].is_const_ptr)
        self.assertFalse(td.type.template_args[0].template_args[0].is_ref)

        # first template arg second template arg
        self.assertEqual(td.type.template_args[0].template_args[1].name, 'long')
        self.assertFalse(td.type.template_args[0].template_args[1].is_const_ptr)
        self.assertTrue(td.type.template_args[0].template_args[1].is_ref)
        self.assertTrue(td.type.template_args[0].template_args[1].is_const)

        # second template arg
        self.assertEqual(td.type.template_args[1].name, 'int')
        self.assertTrue(td.type.template_args[1].is_const)
        self.assertFalse(td.type.template_args[1].is_ref)
        self.assertFalse(td.type.template_args[1].is_ptr)
