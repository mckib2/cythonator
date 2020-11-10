'''Transpile C++ header files to Cython wrappers.'''

import ctypes
import importlib.util
import argparse
import pathlib


def main(header: str, outfile: str):
    libpath = importlib.util.find_spec('transpiler').origin
    _lib = ctypes.cdll.LoadLibrary(libpath)
    _lib.transpile.restype = None
    _lib.transpile.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
    with open(header, 'rb') as fp:
        code = fp.read()
        _lib.transpile(
            code,
            str(pathlib.Path(header).resolve().absolute()).encode(),
            outfile.encode())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='cythonator', description=__doc__)
    parser.add_argument('--header', type=str, help='C++ header file.', required=True)
    parser.add_argument('--output', type=str, help='Cython wrapper file.', default='wrapper.pyx')
    args = parser.parse_args()
    main(header=args.header, outfile=args.output)
