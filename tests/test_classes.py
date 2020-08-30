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
        s = _code_run_single_class([
            f'{self.tagName} MyStruct {{',
            'public:'*self.is_class,
            '    MyStruct() {}',
            '};',
        ])
        self.assertEqual(len(s.methods), 1)
        self.assertTrue(s.methods[0].is_ctor)
        self.assertEqual(len(s.methods[0].function.params), 0)

    def test_ctor(self):
        s = _code_run_single_class([
            f'{self.tagName} MyStruct {{',
            'public:'*self.is_class,
            '    MyStruct(int a, double& b, const float c) {}',
            '};',
        ])
        self.assertEqual(len(s.methods), 1)
        self.assertTrue(s.methods[0].is_ctor)
        ctor = s.methods[0].function
        self.assertEqual(len(ctor.params), 3)
        self.assertEqual(ctor.params[0].name, 'a')
        self.assertTrue(ctor.params[1].type.is_ref)
        self.assertTrue(ctor.params[2].type.is_const)

    def test_dtor(self):
        s = _code_run_single_class([
            f'{self.tagName} MyStruct {{',
            'public:'*self.is_class,
            '    ~MyStruct()=default;',
            '};',
        ])
        # ignore destructors
        self.assertEqual(len(s.methods), 0)

    def test_inheritance(self):
        ns = _code_runner([
            f'{self.tagName} Base {{ }};',
            f'{self.tagName} Child : Base {{ }};',
        ])
        self.assertTrue(len(ns.classes), 2)
        b, c = ns.classes[0], ns.classes[1]
        self.assertEqual(len(b.bases), 0)
        self.assertEqual(len(c.bases), 1)
        self.assertEqual(c.bases[0], 'Base')

    def test_inheritance_from_different_namespace(self):
        ns = _code_runner([
            f'namespace ns {{ {self.tagName} Base {{}}; }}',
            'struct Child : ns::Base {};',
        ])
        b = ns.namespaces[0].classes[0]
        c = ns.classes[0]
        self.assertEqual(len(b.bases), 0)
        self.assertEqual(len(c.bases), 1)
        self.assertEqual(c.bases[0], 'ns::Base')

    def test_removal_of_implicit_functions_from_virtual(self):
        with self.assertWarns(UserWarning):
            s = _code_run_single_class([
                f'{self.tagName} VirtTest {{',
                'public:'*self.is_class,
                '    virtual int myVirtMethod() { return 0; }',
                '};',
            ])
        # Make sure that implicitly generated methods from the virtual
        # function are not included
        self.assertEqual(len(s.methods), 1)

    def test_only_private_methods(self):
        s = _code_run_single_class([
            f'{self.tagName} MyStruct {{',
            'private:',
            '    void mypriv();',
            '    int mypriv2();',
            '    double mypriv3();',
            '    MyStruct* mypriv4();',
            '};',
        ])
        self.assertEqual(len(s.methods), 0)

    def test_protected_methods(self):
        s = _code_run_single_class([
            f'{self.tagName} MyStruct {{',
            'protected:',
            '    void myprot();',
            '    int myprot2();',
            '    double myprot3();',
            '    MyStruct* myprot4();',
            '};',
        ])
        self.assertEqual(len(s.methods), 0)

    def test_mixture_public_protected_private_methods(self):
        s = _code_run_single_class([
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
        ])
        self.assertEqual(len(s.methods), 2)
        self.assertEqual(s.methods[0].function.name, 'mypub')
        self.assertEqual(s.methods[1].function.name, 'mypub2')

    def test_class_template(self):
        s = _code_run_single_class([
            'template<class T>',
            f'{self.tagName} MyStruct {{',
            '};',
        ])
        self.assertEqual(len(s.templateparams), 1)
        self.assertEqual(s.templateparams[0].name, 'T')
        self.assertEqual(s.templateparams[0].tag_used, 'class')

    def test_typename_template(self):
        s = _code_run_single_class([
            'template<typename T>',
            f'{self.tagName} MyStruct {{',
            '};',
        ])
        self.assertEqual(s.templateparams[0].tag_used, 'typename')

    def test_nontype_template(self):
        with self.assertWarns(UserWarning):
            s = _code_run_single_class([
                'template<int N>',
                f'{self.tagName} MyStruct {{',
                'public:'*self.is_class,
                '    double myArray[N];',
                '};',
            ])
        # Cython does not support nontype templates! Should be no params
        self.assertEqual(len(s.templateparams), 0)

    def test_default_template(self):
        s = _code_run_single_class([
            'template<class T, class U, class V = double&>',
            f'{self.tagName} MyStruct {{ }};',
        ])
        self.assertEqual(s.templateparams[0].default, None)
        self.assertEqual(s.templateparams[1].default, None)
        self.assertEqual(s.templateparams[2].default.name, 'double')
        self.assertTrue(s.templateparams[2].default.is_ref)

    def test_template_parameter_pack(self):
        s = _code_run_single_class([
            'template<class T, class ... Types>',
            f'{self.tagName} MyStruct {{ }};',
        ])
        self.assertFalse(s.templateparams[0].is_parameter_pack)
        self.assertTrue(s.templateparams[1].is_parameter_pack)

    def test_unnamed_template_parameter_pack(self):
        s = _code_run_single_class([
            'template<class T, typename...>',
            f'{self.tagName} MyStruct {{ }};',
        ])
        self.assertFalse(s.templateparams[0].is_parameter_pack)
        self.assertTrue(s.templateparams[1].is_parameter_pack)
        self.assertEqual(s.templateparams[1].name, None)

    def test_nested_templates(self):
        with self.assertWarns(UserWarning):
            s = _code_run_single_class([
                'template <class SomeType, template <class> class OtherType>',
                f'{self.tagName} NestedTemplateStruct {{',
                'public:'*self.is_class,
                '    OtherType<SomeType> f;',
                '};',
            ])
        # template-template parameters are currently not supported
        self.assertEqual(len(s.templateparams), 1)

    def test_templated_methods(self):
        s = _code_run_single_class([
            f'{self.tagName} MyStruct {{',
            'public:'*self.is_class,
            '    template<class T, typename U, class V = double *const>',
            '    void myfun(T t, U u, V v);'
            '};',
        ])
        m = s.methods[0].function
        self.assertEqual(m.templateparams[0].name, 'T')
        self.assertEqual(m.templateparams[0].tag_used, 'class')
        self.assertEqual(m.templateparams[1].name, 'U')
        self.assertEqual(m.templateparams[1].tag_used, 'typename')
        self.assertEqual(m.templateparams[2].name, 'V')
        self.assertEqual(m.templateparams[2].tag_used, 'class')
        self.assertEqual(m.templateparams[2].default.name, 'double')
        self.assertTrue(m.templateparams[2].default.is_const_ptr)

    def test_nested_class(self):
        s = _code_run_single_class([
            f'{self.tagName} MyStruct {{',
            'public:'*self.is_class,
            f'    {self.tagName} MyInnerStruct {{}};',
            '};',
        ])
        self.assertEqual(s.name, 'MyStruct')
        self.assertEqual(len(s.classes), 1)
        self.assertEqual(s.classes[0].name, 'MyInnerStruct')

    def test_curiously_recurring_template_pattern(self):
        pass

    def test_typedef(self):
        '''make a typedef inside a struct/class'''
        s = _code_run_single_class([
            f'{self.tagName} MyStruct {{',
            'public:'*self.is_class,
            '    typedef int myInt;',
            '};',
        ])
        self.assertEqual(len(s.typedefs), 1)
        td = s.typedefs[0]
        self.assertEqual(td.name, 'myInt')
        self.assertEqual(td.type.name, 'int')

    def test_data_member_modifiers(self):
        '''Create public data members with various modifiers.'''
        s = _code_run_single_class([
            f'{self.tagName} MyStruct {{',
            'public:'*self.is_class,
            '    int myInt;',
            '    int& myInt_ref;',
            '    int* myInt_star;',
            '    const int const_myInt;',
            '    int *const myInt_star_const;',
            '};',
        ])
        self.assertEqual(s.fields[0].name, 'myInt')
        self.assertEqual(s.fields[1].name, 'myInt_ref')
        self.assertTrue(s.fields[1].type.is_ref)
        self.assertEqual(s.fields[2].name, 'myInt_star')
        self.assertTrue(s.fields[2].type.is_ptr)
        self.assertEqual(s.fields[3].name, 'const_myInt')
        self.assertTrue(s.fields[3].type.is_const)
        self.assertEqual(s.fields[4].name, 'myInt_star_const')
        self.assertTrue(s.fields[4].type.is_ptr)
        self.assertTrue(s.fields[4].type.is_const_ptr)

    # def test_templated_data_members(self):
    #     ns = _code_runner([
    #         'template<class U>',
    #         f'{self.tagName} T {{ }};',
    #         '',
    #         f'{self.tagName} MyStructI {{',
    #         'public:'*self.is_class,
    #         '    T<int> myInt;',
    #         '    T<int&> myInt_ref;',
    #         '    T<int*> myInt_star;',
    #         '    T<const int> const_myInt;',
    #         '    T<int *const> myInt_star_const;',
    #         '};',
    #     ])
    #     print(ns)

class TestClasses(TestStructs):
    def setUp(self):
        self.tagName = 'class'
        self.is_class = True


if __name__ == '__main__':
    unittest.main()
