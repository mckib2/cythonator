from tempfile import NamedTemporaryFile
import subprocess
import pathlib

from cythonator import cythonator
from cythonator.write_cython import write_pxd


def _code_runner(code):
    if isinstance(code, list):
        code = '\n'.join(code)
    with NamedTemporaryFile(suffix='.hpp') as fp, NamedTemporaryFile(suffix='.pyx') as pyxfp, NamedTemporaryFile(suffix='.cpp') as cyfp:
        fp.write(code.encode())
        fp.flush()

        ns = cythonator(filename=fp.name)

        pxd = write_pxd(ns, fp.name)
        print(pxd)
        pyxfp.write(pxd.encode())
        pyxfp.flush()

        # try building the generated cython
        res = subprocess.run([
            'cython', '-3', '--cplus',
            '-o', cyfp.name,
            '-I', str(pathlib.Path(fp.name).parent),
            pyxfp.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            print(res.stderr.decode())
            raise ValueError('Could not compile generated Cython code!')

        return ns


def _code_run_single_fun(code):
    return _code_runner(code).children[0]


def _code_run_single_class(code):
    return _code_runner(code).children[0]


def _code_run_single_typedef(code):
    return _code_runner(code).children[0]
