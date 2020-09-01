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

    # Recursively handle inner structs/classes
    if c.classes:
        pxd += TAB*indent_lvl + '# CLASSES\n'
    for ic in c.classes:
        pxd += _print_class(ic, indent_lvl)

    if not (c.typedefs or c.fields or c.methods or c.classes):
        pxd += TAB*indent_lvl + 'pass\n'

    indent_lvl -= 1
    return pxd


def write_pxd(namespace, headerfile: str, indent_lvl=0):
    '''Translate a namespace tree into a PXD file.'''

    pxd = ''
    pxd += TAB*indent_lvl + 'cdef extern from "{headerfile}"{namespace} nogil:\n'.format(
        headerfile=pathlib.Path(headerfile).resolve(),
        namespace='' if not namespace.name else f' namespace "{namespace.name}"',
    )
    indent_lvl += 1

    # Typedefs
    if namespace.typedefs:
        pxd += TAB*indent_lvl + '# TYPEDEFS\n'
    for t in namespace.typedefs:
        pxd += _print_typedef(t, indent_lvl)

    # Functions
    # TODO: handle redeclaration
    if namespace.functions:
        pxd += TAB*indent_lvl + '# FUNCTIONS\n'
    for f in namespace.functions:
        pxd += _print_function(f, indent_lvl)

    # Structs/classes
    pxd += TAB*indent_lvl + '# CLASSES\n'
    for c in namespace.classes:
        pxd += _print_class(c, indent_lvl)

    # Recursively handle inner namespaces
    if namespace.namespaces:
        pxd += TAB*indent_lvl + '# NAMESPACES\n'
    for ns in namespace.namespaces:
        # print(headerfile)
        print(namespace)
        pxd += write_pxd(
            ns, headerfile, indent_lvl=indent_lvl)

    print(pxd)


if __name__ == '__main__':
    pass
