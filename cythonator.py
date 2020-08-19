'''Transpile C/C++ headers into Cython extensions.'''

import subprocess
import pathlib
import json
from collections import namedtuple

# from parse_xml import parse

Type = namedtuple('Type', 'name is_ref is_ptr is_const')
Typedef = namedtuple('Typedef', 'id name type referenced')
TemplateParam = namedtuple('TemplateParam', 'id name referenced tag_used')
Param = namedtuple('Param', 'id name type')
Function = namedtuple(
    'Function',
    'id name previously_declared return_type params templateparams')
Namespace = namedtuple('Namespace', 'id name functions')


def _is_const(type_str):
    type_str = type_str.strip()
    cond1 = len(type_str) > len('const ') and type_str[:len('const ')+1] == 'const '
    cond2 = len(type_str) > len(' const') and type_str[:-len(' const')] == ' const'
    if cond1 or cond2:
        return True
    return False


def _sanitize_type_str(type_str):
    type_str = type_str.strip()
    type_str = type_str.replace('*', '').replace('&', '').strip()
    if len(type_str) > len('const ') and 'const ' == type_str[:len('const ')]:
        type_str = type_str[len('const '):].strip()
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
        ),
        referenced='isReferenced' in node,
    )

def handle_function(node):

    templateparams = ()
    if node['kind'] == 'FunctionTemplateDecl':
        # handle TemplateParams here
        # TODO: doesn't handle nested templates yet
        templateparams = [TemplateParam(
            id=t['id'],
            name=t['name'],
            referenced='isReferenced' in t and t['isReferenced'],
            tag_used=t['tagUsed'],
        ) for t in node['inner'] if t['kind'] == 'TemplateTypeParmDecl']

        # FunctionTemplateDecl contains FunctionDecl
        node = [l for l in node['inner'] if l['kind'] == 'FunctionDecl'][0]

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
        functions=[handle_function(f) for f in node['inner'] if f['kind'] in {'FunctionDecl', 'FunctionTemplateDecl'}]
    )


def cythonator(files: list, clang_exe='clang++-10'):
    '''C/C++ -> Cython.'''

    # Process the sources
    proc = subprocess.Popen(
        [clang_exe, '-Xclang', '-ast-dump=json', '-fsyntax-only'] + files,
        stdout=subprocess.PIPE)
    out, _err = proc.communicate()

    # with open('ast.json', 'wb') as fp:
    #     fp.write(out)

    ast = json.loads(out)

    # print(list(ast['inner'][-1].keys()))
    # print(ast['inner'][-1]['inner'])

    typedefs = []
    functions = []
    namespaces = []
    for node in ast['inner']:
        if node['kind'] in {'FunctionDecl', 'FunctionTemplateDecl'}:
            functions.append(handle_function(node))
        elif node['kind'] == 'NamespaceDecl':
            namespaces.append(handle_namespace(node))
        elif node['kind'] == 'TypedefDecl':
            # ignore double underscored typedefs
            if node['name'].startswith('__'):
                continue
            typedefs.append(handle_typedef(node))
        elif node['kind'] == 'CXXRecordDecl':
            # both structs and classes
            print(node)
        else:
            print(node['kind'])

    for f in functions:
        print(f)
    for n in namespaces:
        print(n)
    for t in typedefs:
        print(t)


if __name__ == '__main__':

    infiles = [
        # 'tests/void_function_no_args.hpp',
        # 'tests/typed_function_no_args.hpp',
        # 'tests/headers/functions.hpp',
        'tests/headers/simple.hpp',
    ]

    cythonator([str(pathlib.Path(f).resolve()) for f in infiles])
