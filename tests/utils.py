from tempfile import NamedTemporaryFile

from cythonator import cythonator

def _code_runner(code):
    with NamedTemporaryFile(suffix='.hpp') as fp:
        fp.write(code.encode())
        fp.flush()
        return cythonator(filename=fp.name)


def _code_run_single_fun(code):
    return _code_runner(code).functions[0]


def _code_run_single_class(code):
    return _code_runner(code).classes[0]
