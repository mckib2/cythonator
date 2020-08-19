'''Transpile C/C++ headers into Cython extensions.'''

from tempfile import TemporaryDirectory, NamedTemporaryFile
import subprocess
import pathlib

from parse_xml import parse


def cythonator(files: list):
    '''C/C++ -> Cython.'''

    # Process the header files
    with TemporaryDirectory() as dp, NamedTemporaryFile() as fp:
        doxyfile = []
        doxyfile.append("QUIET = YES")
        doxyfile.append("GENERATE_XML = YES")
        doxyfile.append("GENERATE_HTML = NO")
        doxyfile.append("GENERATE_LATEX = NO")
        doxyfile.append("XML_PROGRAMLISTING = NO")
        doxyfile.append('FORCE_LOCAL_INCLUDES = YES')
        doxyfile.append('ENABLE_PREPROCESSING = YES')
        doxyfile.append('SEARCH_INCLUDES = YES')
        doxyfile.append("EXTRACT_ALL = YES")
        doxyfile.append("INPUT = " + ' '.join(files))
        fp.write(('\n'.join(doxyfile)).encode())
        fp.flush()

        proc = subprocess.Popen(
            ['doxygen', fp.name],
            stdout=subprocess.PIPE, cwd=str(dp))
        print(proc.stdout.read())

        # Combine the XML files
        proc = subprocess.Popen(
            ['xsltproc', '--output', 'all.xml', 'combine.xslt', 'index.xml'],
            stdout=subprocess.PIPE,
            cwd=str(pathlib.Path(dp) / 'xml'))
        print(proc.stdout.read())

        # Parse the XML
        parse(str(pathlib.Path(str(dp)) / 'xml/all.xml'))


if __name__ == '__main__':

    infiles = [
        # 'tests/void_function_no_args.hpp',
        # 'tests/typed_function_no_args.hpp',
        'tests/headers/functions.hpp',
    ]

    cythonator([str(pathlib.Path(f).resolve()) for f in infiles])
