'''Traverse the AST and prettyprint Cython.'''

import pathlib
from collections import namedtuple
from keyword import iskeyword

TAB = '    '

Typedef = namedtuple('Typedef', 'id name type referenced')


def _type_str(t):
    # s = t.name
    # if t.is_ref:
    #     s += '&'*t.clang_str.count('&')
    # elif t.is_ptr:
    #     if t.is_const_ptr:
    #         s += ' *const'
    #     else:
    #         s += '*'*t.clang_str.count('*')
    # if t.is_const:
    #     s = 'const ' + s
    # return s
    return t.clang_str.replace('<', '[').replace('>', ']').strip()


def _safe_name(name):
    return name + '_'*iskeyword(name)


def _arg_str(params):
    args = []
    for p in params:
        arg = _type_str(p.type)
        if p.name:
            arg += ' ' + _safe_name(p.name)
        args.append(arg)
    return ', '.join(args)


def _templ_str(params):
    # TODO: handle nested templates!
    templs = ', '.join([_safe_name(p.name) for p in params])
    if templs:
        return '[{templs}]'.format(templs=templs)
    return ''


def _print_typedef(t, indent_lvl):

    # Cython can get confused with nested typedefs (especially with
    # templates), so let's separate things out
    td = ''
    subs = {}
    workaround_prefix = '_cython_nested_templated_typedef_workaround_'
    for ta in t.type.template_args:
        if ta.template_args:
            td += _print_typedef(Typedef(
                id=-1,
                name=workaround_prefix + ta.name,
                type=ta,
                referenced=True
            ), indent_lvl)
            subs[_type_str(ta)] = workaround_prefix + ta.name

    # Use subs to replace nested templated parameters
    type_str = _type_str(t.type)
    for s in subs:
        type_str = type_str.replace(s, subs[s])

    return td + TAB*indent_lvl + f'ctypedef {type_str} {_safe_name(t.name)}\n'


def _print_field(f, indent_lvl):
    return TAB*indent_lvl + '{type} {name}\n'.format(
        type=_type_str(f.type),
        name=_safe_name(f.name),
    )


def _print_function(f, indent_lvl):
    return TAB*indent_lvl + 'cdef {ret_type} {name}{templates}({args})\n'.format(
        ret_type=_type_str(f.return_type),
        name=_safe_name(f.name),
        templates=_templ_str(f.templateparams),
        args=_arg_str(f.params),
    )


def _print_method(m, indent_lvl):
    f = m.function
    if m.is_ctor:
        return TAB*indent_lvl + '{name}{templates}({args}) except +\n'.format(
            name=_safe_name(f.name),
            templates=_templ_str(f.templateparams),
            args=_arg_str(f.params),
        )
    return TAB*indent_lvl + '{ret_type} {name}{templates}({args})\n'.format(
        ret_type=_type_str(f.return_type),
        name=_safe_name(f.name),
        templates=_templ_str(f.templateparams),
        args=_arg_str(f.params),
    )


def _print_class(c, indent_lvl):
    pxd = ''
    pxd += TAB*indent_lvl + 'cppclass {name}{templates}:\n'.format(
        name=_safe_name(c.name),
        templates=_templ_str(c.templateparams),
    )

    indent_lvl += 1
    for t in c.typedefs:
        pxd += _print_typedef(t, indent_lvl)

    for f in c.fields:
        pxd += _print_field(f, indent_lvl)

    for m in c.methods:
        pxd += _print_method(m, indent_lvl)

    # Recursively handle children
    for ic in c.children:
        if ic.__class__.__name__ == 'Class':
            pxd += _print_class(ic, indent_lvl)

    if not (c.typedefs or c.fields or c.methods or c.children):
        pxd += TAB*indent_lvl + 'pass\n'

    indent_lvl -= 1
    return pxd


def _print_extern(namespace, headerfile, indent_lvl):
    return TAB*indent_lvl + 'cdef extern from "{headerfile}"{namespace} nogil:\n'.format(
        headerfile=pathlib.Path(headerfile).resolve(),
        namespace='' if not namespace.name else f' namespace "{namespace.name}"',
    )


def write_pxd(namespace, headerfile: str, indent_lvl=0):
    '''Translate a namespace tree into a PXD file.'''

    pxd = ''

    # handle children in order
    for child in namespace.children:
        typestr = child.__class__.__name__
        if typestr == 'Typedef':
            pxd += _print_extern(namespace, headerfile, indent_lvl)
            pxd += _print_typedef(child, indent_lvl+1)
        elif typestr == 'Function':
            # TODO: handle redeclaration
            pxd += _print_extern(namespace, headerfile, indent_lvl)
            pxd += _print_function(child, indent_lvl+1)
        elif typestr == 'Class':
            pxd += _print_extern(namespace, headerfile, indent_lvl)
            pxd += _print_class(child, indent_lvl+1)
        elif typestr == 'Namespace':
            # Start a new extern block for this namespace
            pxd += write_pxd(
                child, headerfile, indent_lvl=0)

    return pxd


if __name__ == '__main__':
    pass
