'''Transpile C/C++ headers into Cython extensions.'''

import subprocess
import json
from collections import namedtuple
import argparse
import re
import logging

from cythonator.write_cython import write_pxd

Type = namedtuple('Type', 'name is_ref is_ptr is_const is_const_ptr')
Typedef = namedtuple('Typedef', 'id name type referenced')
TemplateParam = namedtuple('TemplateParam', 'id name referenced tag_used default')
Param = namedtuple('Param', 'id name type')
Class = namedtuple(
        'Class',
        'id name is_struct methods fields templateparams bases typedefs')
Function = namedtuple(
    'Function',
    'id name previously_declared return_type params templateparams')
Method = namedtuple('Method', 'function is_ctor')
Field = namedtuple('Field', 'id name type')
Namespace = namedtuple(
    'Namespace',
    'id name functions typedefs namespaces classes')


def _is_const(type_str):
    type_str = type_str.strip()
    if len(type_str) > len('const ') and type_str[:len('const ')] == 'const ':
        return True
    return False


def _is_const_ptr(type_str):
    type_str = type_str.strip().split()
    return '*const' in type_str


def _sanitize_type_str(type_str):
    type_str = type_str.replace('*', '').replace('&', '').strip()
    type_str = ' '.join([t for t in type_str.split() if t != 'const'])
    return type_str


def handle_typedef(node):
    # NOTE: we can get aliases here if we needed them
    return Typedef(
        id=node['id'],
        name=node['name'],
        type=Type(
            name=_sanitize_type_str(node['type']['qualType']),
            is_ref='&' in node['type']['qualType'],
            is_ptr='*' in node['type']['qualType'],
            is_const=_is_const(node['type']['qualType']),
            is_const_ptr=_is_const_ptr(node['type']['qualType']),
        ),
        referenced='isReferenced' in node,
    )


def handle_function(node):
    templateparams = ()
    if node['kind'] == 'FunctionTemplateDecl':
        print(node)
        # handle TemplateParams here
        # TODO: doesn't handle nested templates yet
        templateparams = [TemplateParam(
            id=t['id'],
            name=t['name'],
            referenced='isReferenced' in t and t['isReferenced'],
            tag_used=t['tagUsed'],
        ) for t in node['inner'] if t['kind'] == 'TemplateTypeParmDecl']

        nonTypeTemplateParams = [
            t['type']['qualType'] + ' ' + t['name']
            for t in node['inner']
            if t['kind'] == 'NonTypeTemplateParmDecl']
        if nonTypeTemplateParams:
            logging.warning(
                f'Non-type template parameters {set(nonTypeTemplateParams)} of'
                f' the function "{node["name"]}" are not supported by Cython '
                'and will be omitted from the template parameter list!')

        # FunctionTemplateDecl contains FunctionDecl or CXXMethodDecl
        node = [l for l in node['inner'] if l['kind'] in {'FunctionDecl', 'CXXMethodDecl'}][0]

    # Will this split always work?
    types = node['type']['qualType'].split('(')
    params = ()
    if isinstance(types, str):
        ret_type = types.strip()
    elif len(types) == 2:
        ret_type = types[0].strip()

        # 'inner' may have param info
        if 'inner' in node:
            params = [Param(
                id=l['id'],
                name=l['name'] if 'name' in l else None,
                type=Type(
                    name=_sanitize_type_str(l['type']['qualType']),
                    is_ref='&' in l['type']['qualType'],
                    is_ptr='*' in l['type']['qualType'],
                    is_const=_is_const(l['type']['qualType']),
                    is_const_ptr=_is_const_ptr(l['type']['qualType']),
                ),
            ) for l in node['inner'] if l['kind'] == 'ParmVarDecl']

    else:
        raise NotImplementedError('Split type in way not anticipated!')

    previously_declared = 'previousDecl' in node
    if previously_declared:
        raise NotImplementedError('Need naming scheme for overloads '
                                  'and template specializations!')

    return Function(
        id=node['id'],
        name=node['name'],
        previously_declared=previously_declared,
        return_type=Type(
            name=_sanitize_type_str(ret_type),
            is_ref='&' in ret_type,
            is_ptr='*' in ret_type,
            is_const=_is_const(ret_type),
            is_const_ptr=_is_const_ptr(ret_type),
        ),
        params=params,
        templateparams=templateparams,
    )


def handle_namespace(node):
    if 'inner' not in node:
        node['inner'] = []

    return Namespace(
        id=node['id'],
        name=node['name'],
        functions=[handle_function(f) for f in node['inner'] if f['kind'] in {'FunctionDecl', 'FunctionTemplateDecl'}],
        typedefs=[handle_typedef(t) for t in node['inner'] if t['kind'] == 'TypedefDecl'],
        namespaces=[handle_namespace(n) for n in node['inner'] if n['kind'] == 'NamespaceDecl'] and 'name' in node,
        classes=[handle_class(c) for c in node['inner'] if c['kind'] in {'CXXRecordDecl', 'ClassTemplateDecl'}],
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

    # Keep a list of all the base classes we inherit from;
    # We currently don't keep track of access (public, private, etc.),
    # but that information is available here
    bases = ()
    if 'bases' in node:
        bases = [b['type']['qualType'] for b in node['bases']]

    # If it's a templated class, handle that first
    templateparams = ()
    nonTypeTemplateParams = ()
    if node['kind'] == 'ClassTemplateDecl':
        # handle TemplateParams here
        # TODO: doesn't handle nested templates yet
        templateparams = [TemplateParam(
            id=t['id'],
            name=t['name'],
            referenced='isReferenced' in t and t['isReferenced'],
            tag_used=t['tagUsed'],
            default=Type(
                name=_sanitize_type_str(t['defaultArg']['type']['qualType']),
                is_ref='&' in t['defaultArg']['type']['qualType'],
                is_ptr='*' in t['defaultArg']['type']['qualType'],
                is_const=_is_const(t['defaultArg']['type']['qualType']),
                is_const_ptr=_is_const_ptr(t['defaultArg']['type']['qualType']),
            ) if 'defaultArg' in t else None,
        ) for t in node['inner'] if t['kind'] == 'TemplateTypeParmDecl']

        # TODO: move this code and the copy in handle_function to a separate shared function
        nonTypeTemplateParams = [
            t['type']['qualType'] + ' ' + t['name']
            for t in node['inner']
            if t['kind'] == 'NonTypeTemplateParmDecl']

        # FunctionTemplateDecl contains CXXRecordDecl
        node = [l for l in node['inner'] if l['kind'] == 'CXXRecordDecl'][0]

    # If there is no inner, then this is usually just a declaration
    if 'inner' not in node:
        node['inner'] = []

    # Warn about Cython's lack of support for virtual functions
    virt_funcs = [n['name'] for n in node['inner'] if 'virtual' in n]
    if virt_funcs:
        logging.warning(f'Cython does not support virtual interfaces '
                        f'for functions {set(virt_funcs)} in class '
                        f'"{node["name"]}"!')

    # Warn about any non-type template params we encountered
    if nonTypeTemplateParams:
        # print(json.dumps(node, indent=4))
        logging.warning(
            f'Non-type template parameters {set(nonTypeTemplateParams)} of'
            f' the {node["tagUsed"]} "{node["name"]}" are not supported by Cython '
            'and will be omitted from the template parameter list!')

    # Deduce the access specifier of each entry in node['inner']
    current_access = 'private' if node['tagUsed'] == 'class' else 'public'
    for ii, thing in enumerate(node['inner']):
        if thing['kind'] in {'CXXConstructorDecl', 'CXXMethodDecl', 'FunctionTemplateDecl', 'FieldDecl'}:
            node['inner'][ii]['access'] = current_access
        elif thing['kind'] == 'AccessSpecDecl':
            current_access = thing['access']

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
            type=Type(
                name=_sanitize_type_str(f['type']['qualType']),
                is_ref='&' in f['type']['qualType'],
                is_ptr='*' in f['type']['qualType'],
                is_const=_is_const(f['type']['qualType']),
                is_const_ptr=_is_const_ptr(f['type']['qualType']),
            ),
        ) for f in node['inner'] if f['kind'] == 'FieldDecl' and f['access'] == 'public'],
        templateparams=templateparams,
        bases=bases,
        typedefs=[handle_typedef(t) for t in node['inner'] if t['kind'] == 'TypedefDecl'],
    )


def _get_all_types(thing):
    '''Find all types present in a "thing".'''

    parsable = repr(thing)

    # Find everything that looks like a type
    types = set()
    for match in re.finditer(r"Type\(name='(?P<name>\w+)', is_ref=(?P<is_ref>\w+), is_ptr=(?P<is_ptr>\w+), is_const=(?P<is_const>\w+)\)", parsable):
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
        functions=[],
        typedefs=[],
        namespaces=[],
        classes=[],
    )
    for node in ast['inner']:
        if node['kind'] in {'FunctionDecl', 'FunctionTemplateDecl'}:
            # print(node)
            global_namespace.functions.append(handle_function(node))
        elif node['kind'] == 'NamespaceDecl' and 'name' in node: # ignore anonymous namespaces
            global_namespace.namespaces.append(handle_namespace(node))
        elif node['kind'] == 'TypedefDecl':
            # ignore double underscored typedefs
            if node['name'].startswith('__'):
                continue
            global_namespace.typedefs.append(handle_typedef(node))
        elif node['kind'] in {'CXXRecordDecl', 'ClassTemplateDecl'}:
            # both structs and classes
            # print(json.dumps(node, indent=4))
            global_namespace.classes.append(handle_class(node))
            # print(handle_class(node))
        else:
            print(node['kind'])

    # print(global_namespace)
    # write_pxd(global_namespace, filename)
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
