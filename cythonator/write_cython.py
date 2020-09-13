'''Traverse the AST and prettyprint Cython.'''

import pathlib

TAB = '    '


def _type_str(t):
    s = t.name
    if t.is_ref:
        s += '&'
    elif t.is_ptr:
        if t.is_const_ptr:
            s += ' *const'
        else:
            s += '*'
    if t.is_const:
        s = 'const ' + s
    return s


def _arg_str(params):
    args = []
    for p in params:
        arg = _type_str(p.type)
        if p.name:
            arg += ' ' + p.name
        args.append(arg)
    return ', '.join(args)


def _templ_str(params):
    # TODO: handle nested templates!
    templs = ', '.join([p.name for p in params if p.referenced])
    if templs:
        return '[{templs}]'.format(templs=templs)
    return ''


def _print_typedef(t, indent_lvl):
    return TAB*indent_lvl + 'ctypedef {type} {alias}\n'.format(
        type=_type_str(t.type),
        alias=t.name,
    )


def _print_field(f, indent_lvl):
    return TAB*indent_lvl + '{type} {name}\n'.format(
        type=_type_str(f.type),
        name=f.name,
    )


def _print_function(f, indent_lvl):
    return TAB*indent_lvl + 'cdef {ret_type} {name}{templates}({args})\n'.format(
        ret_type=_type_str(f.return_type),
        name=f.name,
        templates=_templ_str(f.templateparams),
        args=_arg_str(f.params),
    )


def _print_method(m, indent_lvl):
    f = m.function
    if m.is_ctor:
        return TAB*indent_lvl + '{name}{templates}({args}) except +\n'.format(
            name=f.name,
            templates=_templ_str(f.templateparams),
            args=_arg_str(f.params),
        )
    return TAB*indent_lvl + '{ret_type} {name}{templates}({args})\n'.format(
        ret_type=_type_str(f.return_type),
        name=f.name,
        templates=_templ_str(f.templateparams),
        args=_arg_str(f.params),
    )


def _print_class(c, indent_lvl):
    pxd = ''
    pxd += TAB*indent_lvl + 'cdef cppclass {name}{templates}:\n'.format(
        name=c.name,
        templates=_templ_str(c.templateparams),
    )

    indent_lvl += 1
    if c.typedefs:
        pxd += TAB*indent_lvl + '# TYPEDEFS\n'
    for t in c.typedefs:
        pxd += _print_typedef(t, indent_lvl)

    if c.fields:
        pxd += TAB*indent_lvl + '# DATA MEMBERS\n'
    for f in c.fields:
        pxd += _print_field(f, indent_lvl)

    if c.methods:
        pxd += TAB*indent_lvl + '# METHODS\n'
    for m in c.methods:
        pxd += _print_method(m, indent_lvl)

    # Recursively handle children
    if c.children:
        pxd += TAB*indent_lvl + '# CHILDREN\n'
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
