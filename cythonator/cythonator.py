'''Transpile C/C++ headers into Cython extensions.'''

import subprocess
import json
from collections import namedtuple
import argparse
import re
from warnings import warn

from cythonator.write_cython import write_pxd


# Custom AST nodes -- I don't think Cython ones currently do all the
# things we need
Type = namedtuple(
    'Type',
    'name is_ref is_ptr is_const is_const_ptr is_arr template_args clang_str')
Typedef = namedtuple('Typedef', 'id name type referenced')
TemplateParam = namedtuple(
    'TemplateParam',
    'id name referenced tag_used default is_parameter_pack')
Param = namedtuple('Param', 'id name type')
Class = namedtuple(
        'Class',
        'id name is_struct methods fields templateparams bases typedefs children')
Function = namedtuple(
    'Function',
    'id name previously_declared return_type params templateparams')
Method = namedtuple('Method', 'function is_ctor')
Field = namedtuple('Field', 'id name type')
Namespace = namedtuple(
    'Namespace',
    'id name children')


def _is_const(type_str):
    type_str = _remove_template_part(type_str).strip()
    if len(type_str) > len('const ') and type_str[:len('const ')] == 'const ':
        return True
    return False


def _is_const_ptr(type_str):
    type_str = _remove_template_part(type_str).split()
    return '*const' in type_str


def _remove_template_part(type_str):
    # Remove any template part of the string
    start_idx = type_str.find('<')
    end_idx = type_str.rfind('>')
    if start_idx > 0:
        type_str = type_str[:start_idx] + type_str[end_idx+1:]
    return type_str.strip()


def _is_ptr(type_str):
    return '*' in _remove_template_part(type_str)


def _is_ref(type_str):
    return '&' in _remove_template_part(type_str)


def _is_arr(type_str):
    return '[' in _remove_template_part(type_str)


def _sanitize_type_str(type_str):
    type_str = _remove_template_part(type_str)
    type_str = type_str.replace('*', '').replace('&', '').strip()
    type_str = ' '.join([t for t in type_str.split() if t != 'const'])
    type_str = type_str.split('()')[0].strip()
    return type_str


def _get_template_args(type_str):
    # If there is a template, we need to recursively resolve it
    if '<' not in type_str:
        return []

    # Take contents of the outermost angle bracket pair
    start_idx = type_str.find('<')
    end_idx = type_str.rfind('>')
    template_str = type_str[start_idx+1:end_idx].strip()

    # This could be a comma separated list of potentially templated
    # types, so separate the types and call recursively to get the
    # final list
    # NOTE: we could also create a dummy class to take the parameters
    # and call clang recursively, but this will probably work, too
    idx = 0
    tipe = ''
    braces = 0
    types = []
    recurse = False
    while idx < len(template_str):
        # Eat the next type
        if template_str[idx] == '<':
            braces += 1
            recurse = True
        if template_str[idx] == '>':
            braces -= 1
        if braces == 0 and template_str[idx] == ',' and recurse:
            # print('tipe before recurse is', tipe)
            # types.append(_get_template_args(tipe)[0])
            types.append(Type(
                name=_sanitize_type_str(tipe),
                is_ref=_is_ref(tipe),
                is_ptr=_is_ptr(tipe),
                is_const=_is_const(tipe),
                is_const_ptr=_is_const_ptr(tipe),
                is_arr=_is_arr(tipe),
                template_args=_get_template_args(tipe),
                clang_str=tipe,
            ))
            tipe = ''
            recurse = False
        elif braces == 0 and template_str[idx] == ',':
            types.append(Type(
                name=_sanitize_type_str(tipe),
                is_ref=_is_ref(tipe),
                is_ptr=_is_ptr(tipe),
                is_const=_is_const(tipe),
                is_const_ptr=_is_const_ptr(tipe),
                is_arr=_is_arr(tipe),
                template_args=[],  # did not recurse
                clang_str=tipe,
            ))
            tipe = ''
        else:
            tipe = tipe + template_str[idx]
            if idx == len(template_str) - 1:
                types.append(Type(
                    name=_sanitize_type_str(tipe),
                    is_ref=_is_ref(tipe),
                    is_ptr=_is_ptr(tipe),
                    is_const=_is_const(tipe),
                    is_const_ptr=_is_const_ptr(tipe),
                    is_arr=_is_arr(tipe),
                    template_args=[],  # did not recurse
                    clang_str=tipe,
                ))

        idx += 1

    return types


def handle_type(t):
    if not isinstance(t, str):
        t = t['qualType']

    return Type(
        name=_sanitize_type_str(t),
        is_ref=_is_ref(t),
        is_ptr=_is_ptr(t),
        is_const=_is_const(t),
        is_const_ptr=_is_const_ptr(t),
        is_arr=_is_arr(t),
        template_args=_get_template_args(t),
        clang_str=t,
    )


def handle_typedef(node):
    # NOTE: we can get aliases here if we needed them
    return Typedef(
        id=node['id'],
        name=node['name'],
        type=handle_type(node['type']),
        referenced='isReferenced' in node,
    )


def handle_function(node):
    templateparams = ()
    if node['kind'] == 'FunctionTemplateDecl':
        # handle TemplateParams here
        # TODO: doesn't handle nested templates yet
        templateparams = [TemplateParam(
            id=t['id'],
            name=t['name'] if 'name' in t else None,
            referenced='isReferenced' in t and t['isReferenced'],
            tag_used=t['tagUsed'],
            default=handle_type(t['defaultArg']['type']) if 'defaultArg' in t else None,
            is_parameter_pack='isParameterPack' in t and t['isParameterPack'],
        ) for t in node['inner'] if t['kind'] == 'TemplateTypeParmDecl']

        nonTypeTemplateParams = [
            t['type']['qualType'] + ' ' + t['name']
            for t in node['inner']
            if t['kind'] == 'NonTypeTemplateParmDecl']
        if nonTypeTemplateParams:
            warn(
                f'Non-type template parameters {set(nonTypeTemplateParams)} of'
                f' the function "{node["name"]}" are not supported by Cython '
                'and will be omitted from the template parameter list!')

        # FunctionTemplateDecl contains FunctionDecl or CXXMethodDecl
        node = [l for l in node['inner'] if l['kind'] in {'FunctionDecl', 'CXXMethodDecl'}][0]

    # eat the return type
    ret_type = ''
    ii = 0
    next_char = node['type']['qualType'][ii]
    while next_char != '(':
        ret_type += next_char
        ii += 1
        next_char = node['type']['qualType'][ii]

    # Get the function params
    if 'inner' in node:
        params = [Param(
                id=l['id'],
                name=l['name'] if 'name' in l else None,
                type=handle_type(l['type']),
            ) for l in node['inner'] if l['kind'] == 'ParmVarDecl']
    else:
        params = ()

    previously_declared = 'previousDecl' in node
    if previously_declared:
        raise NotImplementedError('Need naming scheme for overloads '
                                  'and template specializations!')

    return Function(
        id=node['id'],
        name=node['name'],
        previously_declared=previously_declared,
        return_type=handle_type(ret_type),
        params=params,
        templateparams=templateparams,
    )


def handle_namespace(node, parent_node=None):
    if 'inner' not in node:
        node['inner'] = []

    if parent_node is None:
        qualified_ns = node['name']
    else:
        qualified_ns = parent_node['name'] + '::' + node['name']

    # gather all children contained in namespace
    children = []
    for thing in node['inner']:
        if thing['kind'] in {'FunctionDecl', 'FunctionTemplateDecl'}:
            children.append(handle_function(thing))
        elif thing['kind'] == 'TypedefDecl':
            children.append(handle_typedef(thing))
        elif thing['kind'] == 'NamespaceDecl' and 'name' in node:
            children.append(handle_namespace(thing, node))
        elif thing['kind'] in {'CXXRecordDecl', 'ClassTemplateDecl'}:
            children.append(handle_class(thing))

    return Namespace(
        id=node['id'],
        name=qualified_ns,
        children=children,
    )


def handle_class(node):
    '''
    Notes
    -----
    node['inner'] (if it exists) is in the same order as it is declared in the
    header file.  This means access specifiers are given as entries in
    node['inner'] and the [public|private|protected]-ness of the entry in
    node['inner'] must be deduced by its tag ([class|struct]) as well as the
    order it comes in with respect to the last access specifier.
    '''

    # if node['name'] == 'MyStructI':
    #     print(json.dumps(node, indent=4))

    # Keep a list of all the base classes we inherit from;
    # We currently don't keep track of access (public, private, etc.),
    # but that information is available here
    bases = ()
    if 'bases' in node:
        bases = [b['type']['qualType'] for b in node['bases']]

    # If it's a templated class, handle that first
    templateparams = ()
    nonTypeTemplateParams = ()
    templateTemplateParams = ()
    if node['kind'] == 'ClassTemplateDecl':
        # handle TemplateParams here
        # TODO: doesn't handle nested templates yet
        templateparams = [TemplateParam(
            id=t['id'],
            name=t['name'] if 'name' in t else None,
            referenced='isReferenced' in t and t['isReferenced'],
            tag_used=t['tagUsed'],
            default=handle_type(t['defaultArg']['type']) if 'defaultArg' in t else None,
            is_parameter_pack='isParameterPack' in t and t['isParameterPack'],
        ) for t in node['inner'] if t['kind'] == 'TemplateTypeParmDecl']

        # TODO: move this code and the copy in handle_function to a separate shared function
        nonTypeTemplateParams = [
            t['type']['qualType'] + ' ' + t['name']
            for t in node['inner']
            if t['kind'] == 'NonTypeTemplateParmDecl']

        templateTemplateParams = [
            t['name'] for t in node['inner'] if t['kind'] =='TemplateTemplateParmDecl'
        ]

        # FunctionTemplateDecl contains CXXRecordDecl
        node = [l for l in node['inner'] if l['kind'] == 'CXXRecordDecl'][0]

    # If there is no inner, then this is usually just a declaration
    if 'inner' not in node:
        node['inner'] = []

    # Warn about Cython's lack of support for virtual functions
    virt_funcs = [n['name'] for n in node['inner'] if 'virtual' in n]
    if virt_funcs:
        warn(
            f'Cython does not support virtual interfaces '
            f'for functions {set(virt_funcs)} in '
            f'{node["tagUsed"]} "{node["name"]}"!')

    # Warn about any non-type template params we encountered
    if nonTypeTemplateParams:
        warn(
            f'Non-type template parameters {set(nonTypeTemplateParams)} of'
            f' the {node["tagUsed"]} "{node["name"]}" are not supported by Cython '
            'and will be omitted from the template parameter list!')

    # Warn about any template-template paramters we encountered
    if templateTemplateParams:
        warn(
            'Template-template parameters are not supported. Template-'
            f'template parameters {set(templateTemplateParams)} '
            f'of {node["tagUsed"]} "{node["name"]}" will be ignored.')

    # Deduce the access specifier of each entry in node['inner']
    current_access = 'private' if node['tagUsed'] == 'class' else 'public'
    for ii, thing in enumerate(node['inner']):
        if thing['kind'] in {'CXXConstructorDecl', 'CXXMethodDecl', 'FunctionTemplateDecl', 'FieldDecl'}:
            node['inner'][ii]['access'] = current_access
        elif thing['kind'] == 'AccessSpecDecl':
            current_access = thing['access']

    # gather up all children
    children = []
    for thing in node['inner']:
        if thing['kind'] in {'CXXRecordDecl', 'ClassTemplateDecl'} and thing['name'] != node['name']:
            children.append(handle_class(thing))

    return Class(
        id=node['id'],
        name=node['name'],
        is_struct=node['tagUsed'] == 'struct',
        # can add default ctor, movectr, copyctr, copyassign if wanted (look in definitionData)
        # - Ignores implicit functions generated by virtual methods
        # - Ignores non-public methods
        methods=[Method(
            function=handle_function(m),
            is_ctor=m['kind'] == 'CXXConstructorDecl',
        ) for m in node['inner'] if m['kind'] in {'CXXConstructorDecl', 'CXXMethodDecl', 'FunctionTemplateDecl'} and m['access'] == 'public' and ('isImplicit' not in m or not m['isImplicit'])],
        fields=[Field(
            id=f['id'],
            name=f['name'],
            type=handle_type(f['type']),
        ) for f in node['inner'] if f['kind'] == 'FieldDecl' and f['access'] == 'public'],
        templateparams=templateparams,
        bases=bases,
        typedefs=[handle_typedef(t) for t in node['inner'] if t['kind'] == 'TypedefDecl'],
        children=children,
    )


def _get_all_types(thing):
    '''Find all types present in a "thing".'''

    parsable = repr(thing)

    # Find everything that looks like a type
    types = set()
    # TODO: make work with template_args
    for match in re.finditer(r"Type\(name='(?P<name>\w+)', is_ref=(?P<is_ref>\w+), is_ptr=(?P<is_ptr>\w+), is_const=(?P<is_const>\w+)\), template_args=(?P<template_args>\w+)", parsable):
        types.add(match.group('name'))
    return types


def cythonator(filename: str, clang_exe='clang++-10'):
    '''C/C++ -> Cython.'''

    # Process the sources
    proc = subprocess.Popen(
        [clang_exe, '-Xclang', '-ast-dump=json', '-fsyntax-only'] + [filename],
        stdout=subprocess.PIPE)
    out, _err = proc.communicate()

    # with open('ast.json', 'wb') as fp:
    #     fp.write(out)

    ast = json.loads(out)

    # print(list(ast['inner'][-1].keys()))
    # print(ast['inner'][-1]['inner'])

    global_namespace = Namespace(
        id='_global_namespace',
        name='',
        children=[],
    )
    for node in ast['inner']:
        if node['kind'] in {'FunctionDecl', 'FunctionTemplateDecl'}:
            # print(node)
            global_namespace.children.append(handle_function(node))
        elif node['kind'] == 'NamespaceDecl' and 'name' in node:  # ignore anonymous namespaces
            global_namespace.children.append(handle_namespace(node))
        elif node['kind'] == 'TypedefDecl':
            # ignore double underscored typedefs
            if node['name'].startswith('__'):
                continue
            global_namespace.children.append(handle_typedef(node))
        elif node['kind'] in {'CXXRecordDecl', 'ClassTemplateDecl'}:
            # both structs and classes
            # print(json.dumps(node, indent=4))
            global_namespace.children.append(handle_class(node))
            # print(handle_class(node))
        else:
            print(node['kind'])

    # print(global_namespace)
    # pxd = write_pxd(global_namespace, filename)
    # print(pxd)
    # print(_get_all_types(global_namespace))
    return global_namespace


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='C++ -> Cython.')
    parser.add_argument(
        '--header', type=str, help='C++ header file', required=True)
    args = parser.parse_args()

    # infiles = [
    #     # 'tests/void_function_no_args.hpp',
    #     # 'tests/typed_function_no_args.hpp',
    #     # 'tests/headers/functions.hpp',
    #     'tests/headers/simple.hpp',
    # ]
    # cythonator([str(pathlib.Path(f).resolve()) for f in infiles])

    cythonator(args.header)
