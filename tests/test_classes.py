'''Tests on classes/structs.'''

import unittest

from .utils import _code_runner, _code_run_single_class


class TestStructs(unittest.TestCase):

    def setUp(self):
        self.tagName = 'struct'
        self.is_class = False

    def test_declaration(self):
        s = _code_run_single_class(f'{self.tagName} MyStruct;')
        if self.tagName == 'struct':
            self.assertTrue(s.is_struct)
        else:
            self.assertFalse(s.is_struct)
        self.assertEqual(s.name, 'MyStruct')

    def test_only_trivial_ctor(self):
        s = _code_run_single_class('\n'.join([
            f'{self.tagName} MyStruct {{',
            'public:'*self.is_class,
            '    MyStruct() {}',
            '};',
        ]))
        self.assertEqual(len(s.methods), 1)
        self.assertTrue(s.methods[0].is_ctor)
        self.assertEqual(len(s.methods[0].function.params), 0)

    def test_ctor(self):
        s = _code_run_single_class('\n'.join([
            f'{self.tagName} MyStruct {{',
            'public:'*self.is_class,
            '    MyStruct(int a, double& b, const float c) {}',
            '};',
        ]))
        self.assertEqual(len(s.methods), 1)
        self.assertTrue(s.methods[0].is_ctor)
        ctor = s.methods[0].function
        self.assertEqual(len(ctor.params), 3)
        self.assertEqual(ctor.params[0].name, 'a')
        self.assertTrue(ctor.params[1].type.is_ref)
        self.assertTrue(ctor.params[2].type.is_const)

    def test_dtor(self):
        s = _code_run_single_class('\n'.join([
            f'{self.tagName} MyStruct {{',
            'public:'*self.is_class,
            '    ~MyStruct()=default;',
            '};',
        ]))
        # ignore destructors
        self.assertEqual(len(s.methods), 0)

    def test_inheritance(self):
        ns = _code_runner('\n'.join([
            f'{self.tagName} Base {{ }};',
            f'{self.tagName} Child : Base {{ }};',
        ]))
        self.assertTrue(len(ns.classes), 2)
        b, c = ns.classes[0], ns.classes[1]
        self.assertEqual(len(b.bases), 0)
        self.assertEqual(len(c.bases), 1)
        self.assertEqual(c.bases[0], 'Base')

    def test_inheritance_from_different_namespace(self):
        ns = _code_runner('\n'.join([
            f'namespace ns {{ {self.tagName} Base {{}}; }}',
            'struct Child : ns::Base {};',
        ]))
        b = ns.namespaces[0].classes[0]
        c = ns.classes[0]
        self.assertEqual(len(b.bases), 0)
        self.assertEqual(len(c.bases), 1)
        self.assertEqual(c.bases[0], 'ns::Base')

    def test_removal_of_implicit_functions_from_virtual(self):
        s = _code_run_single_class('\n'.join([
            f'{self.tagName} VirtTest {{',
            'public:'*self.is_class,
            '    virtual int myVirtMethod() { return 0; }',
            '};',
            ]))
        # Make sure that implicitly generated methods from the virtual
        # function are not included
        self.assertEqual(len(s.methods), 1)

    def test_only_private_methods(self):
        s = _code_run_single_class('\n'.join([
            f'{self.tagName} MyStruct {{',
            'private:',
            '    void mypriv();',
            '    int mypriv2();',
            '    double mypriv3();',
            '    MyStruct* mypriv4();',
            '};',
        ]))
        self.assertEqual(len(s.methods), 0)

    def test_protected_methods(self):
        s = _code_run_single_class('\n'.join([
            f'{self.tagName} MyStruct {{',
            'protected:',
            '    void myprot();',
            '    int myprot2();',
            '    double myprot3();',
            '    MyStruct* myprot4();',
            '};',
        ]))
        self.assertEqual(len(s.methods), 0)

    def test_mixture_public_protected_private_methods(self):
        s = _code_run_single_class('\n'.join([
            f'{self.tagName} MyStruct {{',
            'private:',
            '    void mypriv();',
            'public:',
            '    int mypub();',
            'private:',
            '    double mypriv2();',
            'public:',
            '    MyStruct* mypub2();',
            'protected:',
            '    short myprot();',
            '};',
        ]))
        self.assertEqual(len(s.methods), 2)
        self.assertEqual(s.methods[0].function.name, 'mypub')
        self.assertEqual(s.methods[1].function.name, 'mypub2')

    def test_class_template(self):
        s = _code_run_single_class('\n'.join([
            'template<class T>',
            f'{self.tagName} MyStruct {{',
            '};',
        ]))
        self.assertEqual(len(s.templateparams), 1)
        self.assertEqual(s.templateparams[0].name, 'T')
        self.assertEqual(s.templateparams[0].tag_used, 'class')

    def test_typename_template(self):
        s = _code_run_single_class('\n'.join([
            'template<typename T>',
            f'{self.tagName} MyStruct {{',
            '};',
        ]))
        self.assertEqual(s.templateparams[0].tag_used, 'typename')

    def test_nontype_template(self):
        code = '\n'.join([
            'template<int N>',
            f'{self.tagName} MyStruct {{',
            '};',
        ])
        s = _code_run_single_class(code)
        # Cython does not support nontype templates! Should be no params
        self.assertEqual(len(s.templateparams), 0)

    def test_default_template(self):
        s = _code_run_single_class('\n'.join([
            'template<class T, class U, class V = double&>',
            f'{self.tagName} MyStruct {{ }};',
        ]))
        self.assertEqual(s.templateparams[0].default, None)
        self.assertEqual(s.templateparams[1].default, None)
        self.assertEqual(s.templateparams[2].default.name, 'double')
        self.assertTrue(s.templateparams[2].default.is_ref)

    def test_template_parameter_pack(self):
        s = _code_run_single_class('\n'.join([
            'template<class T, class ... Types>',
            f'{self.tagName} MyStruct {{ }};',
        ]))
        self.assertFalse(s.templateparams[0].is_parameter_pack)
        self.assertTrue(s.templateparams[1].is_parameter_pack)

    def test_nested_templates(self):
        pass

    def test_templated_methods(self):
        pass

    def test_typedef(self):
        '''make a typedef inside a struct/class'''
        s = _code_run_single_class('\n'.join([
            f'{self.tagName} MyStruct {{',
            'public:'*self.is_class,
            '    typedef int myInt;',
            '};',
        ]))
        self.assertEqual(len(s.typedefs), 1)
        td = s.typedefs[0]
        self.assertEqual(td.name, 'myInt')
        self.assertEqual(td.type.name, 'int')

    def test_fields(self):
        '''Create public data members of various types.'''


class TestClasses(TestStructs):
    def setUp(self):
        self.tagName = 'class'
        self.is_class = True
