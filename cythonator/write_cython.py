'''Write Cython files.'''

import pathlib


def _type_str(t):
    s = t.name
    if t.is_ref:
        s += '&'
    elif t.is_ptr:
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
    templs = ', '.join([p.name for p in params if p.referenced])
    if templs:
        return '[{templs}]'.format(templs=templs)
    return ''


def write_pxd(namespace, headerfile, TAB='    '):
    '''Translate a namespace into a PXD file.'''

    pxd = ''
    pxd += 'cdef extern from "{headerfile}" nogil:\n'.format(
        headerfile=pathlib.Path(headerfile).resolve(),
    )

    # Typedefs
    pxd += TAB + '# TYPEDEFS\n'
    for t in namespace.typedefs:
        pxd += TAB + 'ctypedef {type} {alias}\n'.format(
            type=_type_str(t.type),
            alias=t.name,
        )

    # Functions
    # TODO: handle redeclaration
    pxd += TAB + '# FUNCTIONS\n'
    for f in namespace.functions:
        pxd += TAB + 'cdef {ret_type} {name}{templates}({args})\n'.format(
            ret_type=_type_str(f.return_type),
            name=f.name,
            templates=_templ_str(f.templateparams),
            args=_arg_str(f.params),
        )

    # Recursively handle inner namespaces


    print(pxd)


if __name__ == '__main__':
    pass
