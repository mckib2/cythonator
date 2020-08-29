'''Tests on functions.'''

import unittest
from collections import defaultdict

import numpy as np

from .utils import _code_runner, _code_run_single_fun

class TestFunctionsNoArgs(unittest.TestCase):
    def test_void(self):
        fun = _code_run_single_fun('void void_function_void();')
        self.assertEqual(fun.name, 'void_function_void')
        self.assertEqual(fun.return_type.name, 'void')

    def test_void_star(self):
        fun = _code_run_single_fun('void* void_star_function_void();')
        self.assertEqual(fun.name, 'void_star_function_void')
        self.assertEqual(fun.return_type.name, 'void')
        self.assertEqual(fun.return_type.is_ptr, True)

    def test_const_void_star(self):
        fun = _code_run_single_fun(
            'const void* const_void_star_function_void();')
        self.assertEqual(fun.name, 'const_void_star_function_void')
        self.assertEqual(fun.return_type.name, 'void')
        self.assertEqual(fun.return_type.is_ptr, True)
        self.assertEqual(fun.return_type.is_const, True)

    def test_void_star_const(self):
        fun = _code_run_single_fun(
            'void* const void_star_const_function_void();')
        self.assertEqual(fun.name, 'void_star_const_function_void')
        self.assertEqual(fun.return_type.name, 'void')
        self.assertEqual(fun.return_type.is_ptr, True)
        self.assertEqual(fun.return_type.is_const_ptr, True)
        self.assertEqual(fun.return_type.is_const, False)

    def test_const_void_star_const(self):
        fun = _code_run_single_fun(
            'const void* const const_void_star_const_function_void();')
        self.assertEqual(fun.name, 'const_void_star_const_function_void')
        self.assertEqual(fun.return_type.name, 'void')
        self.assertEqual(fun.return_type.is_ptr, True)
        self.assertEqual(fun.return_type.is_const_ptr, True)
        self.assertEqual(fun.return_type.is_const, True)

    def test_unsigned_short_int(self):
        fun = _code_run_single_fun(
            'unsigned short int unsigned_short_int_function_void();')
        self.assertEqual(fun.name, 'unsigned_short_int_function_void')
        self.assertEqual(fun.return_type.name, 'unsigned short')

    def test_unsigned_short_int_ref(self):
        fun = _code_run_single_fun(
            'unsigned short int& unsigned_short_int_ref_function_void();')
        self.assertEqual(fun.name, 'unsigned_short_int_ref_function_void')
        self.assertEqual(fun.return_type.name, 'unsigned short')
        self.assertEqual(fun.return_type.is_ref, True)

    def test_namespaced_void(self):
        ns = _code_runner('namespace ns { void void_ns_function(); }')
        self.assertEqual(len(ns.functions), 0)
        self.assertEqual(len(ns.namespaces), 1)
        self.assertEqual(len(ns.namespaces[0].functions), 1)
        fun = ns.namespaces[0].functions[0]
        self.assertEqual(fun.name, 'void_ns_function')
        self.assertEqual(fun.return_type.name, 'void')

    def test_templated_int(self):
        fun = _code_run_single_fun(
            'template<typename T> int templated_int_function();')
        self.assertEqual(fun.name, 'templated_int_function')
        self.assertEqual(fun.return_type.name, 'int')
        self.assertEqual(len(fun.templateparams), 1)
        self.assertEqual(fun.templateparams[0].name, 'T')

    def test_multi_templated_int_ref(self):
        fun = _code_run_single_fun(
            'template<typename T, class U> int& templated_int_ref_function();')
        self.assertEqual(fun.name, 'templated_int_ref_function')
        self.assertEqual(fun.return_type.name, 'int')
        self.assertEqual(fun.return_type.is_ref, True)
        self.assertEqual(len(fun.templateparams), 2)
        self.assertEqual(fun.templateparams[0].name, 'T')
        self.assertEqual(fun.templateparams[1].name, 'U')

    def test_non_type_template_param_void(self):
        fun = _code_run_single_fun('template<unsigned int N> void fun();')

        # Currently non-type template parameters should be ignored:
        self.assertEqual(len(fun.templateparams), 0)


class TestFunctionsWithArgs(unittest.TestCase):
    def setUp(self):
        # C types
        self.C_MAIN_TYPES = [
            'void',
            'char',
            'unsigned char',
            'short',
            'unsigned short',
            'int',
            'unsigned int',
            'long',
            'unsigned long',
            'long long',
            'unsigned long long',
            'float',
            'double',
            'long double',
        ]

    # def test_named_c_main_types_single_arg(self):
    #     for t in set(self.C_MAIN_TYPES) - {'void'}:
    #         for u in self.C_MAIN_TYPES:
    #             fun = _code_run_single_fun(f'{u} fun({t} arg);')
    #             self.assertEqual(fun.params[0].name, 'arg')
    #             self.assertEqual(fun.params[0].type.name, t)

    def test_unnamed_c_main_types_multi_args(self):
        num_args = 5
        np.random.seed(0)
        for ii, t in enumerate(self.C_MAIN_TYPES):
            # Argument types
            # exclude 'void' (first element)
            args = np.random.choice(self.C_MAIN_TYPES[1:], size=num_args)
            mods = np.random.choice(['', '*', '&', '*const'], size=num_args)
            consts = np.random.choice(['', 'const'], size=num_args)
            argstring = [c + ' ' + a + ' ' + m for c, a, m in zip(
                consts, args, mods)]
            argstring = ", ".join(argstring)

            # Return type
            mod = np.random.choice(['', '*', '&', '*const'])
            const = np.random.choice(['', 'const'])
            ret = const + ' ' + t + ' ' + mod
            code = f'{ret} fun({argstring});'

            fun = _code_run_single_fun(code)
            for jj, p in enumerate(fun.params):
                self.assertEqual(p.type.name, args[jj])
                self.assertEqual(p.type.is_ref, mods[jj] == '&')
                self.assertEqual(p.type.is_ptr, mods[jj] in {'*', '*const'})
                self.assertEqual(p.type.is_const_ptr, mods[jj] == '*const')
                self.assertEqual(p.type.is_const, consts[jj] == 'const')
            self.assertEqual(fun.return_type.name, t)
            self.assertEqual(fun.return_type.is_ref, mod == '&')
            self.assertEqual(fun.return_type.is_ptr, mod in {'*', '*const'})
            self.assertEqual(fun.return_type.is_const_ptr, mod == '*const')
            self.assertEqual(fun.return_type.is_const, const == 'const')


if __name__ == '__main__':
    unittest.main()
