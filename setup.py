'''Compile clang tools needed '''

import pathlib
import platform
import re
from setuptools import find_packages
from distutils.core import Extension, setup


def _llvm_config(llvm_config_dir, llvm_triple='x86_64-unknown-linux-gnu'):
    config_in = llvm_config_dir / 'llvm-config.h.cmake'
    with open(config_in, 'r') as fp:
        contents = fp.read()

    # Values
    arch = 'X86' if platform.processor() == 'x86_64' else ''
    defines = [
        ('LLVM_DEFAULT_TARGET_TRIPLE', llvm_triple),  # TODO: don't hard-code!
        ('LLVM_HOST_TRIPLE', llvm_triple),
        ('LLVM_NATIVE_ARCH', arch),
        ('LLVM_ON_UNIX', int(platform.system() in {'Linux', 'Darwin'})),
        ('LLVM_VERSION_MAJOR', 0),
        ('LLVM_VERSION_MINOR', 0),
        ('LLVM_VERSION_PATCH', 0),
        ('PACKAGE_VERSION', '0.0.0'),
        ('LLVM_WITH_Z3', 0),
    ]
    for match, val in defines:
        contents = contents.replace('${%s}' % match, str(val))

    # Take care of '#cmakedefine's
    cmakedefines = re.compile(r'#cmakedefine\s(?P<key>\w+)\s?(?P<val>.*)')
    for m in cmakedefines.finditer(contents, re.MULTILINE):
        if not m.group('val'):
            contents = contents.replace(
                m.group(0),
                '/* #undef %s */\n' % m.group('key'))
        else:
            contents = contents.replace(
                m.group(0),
                '#define %s %s' % (m.group('key'), m.group('val')))

    # Define all of these as 0 for now:
    cmakedefines01 = re.compile(r'#cmakedefine01\s(?P<key>\w+)')
    for m in cmakedefines01.finditer(contents, re.MULTILINE):
        contents = contents.replace(
            m.group(0),
            '#define %s 0' % m.group('key'))

    return contents


def _abi_breaking_config(llvm_config_dir):

    with open(llvm_config_dir / 'abi-breaking.h.cmake', 'r') as fp:
        contents = fp.read()

    # Define all of these as 0 for now:
    cmakedefines01 = re.compile(r'#cmakedefine01\s(?P<key>\w+)')
    for m in cmakedefines01.finditer(contents, re.MULTILINE):
        contents = contents.replace(
            m.group(0),
            '#define %s 0' % m.group('key'))
    return contents


def _cmakelists_scrape(base_dir, START_TOKEN, END_TOKEN):
    cmakelists = base_dir / 'CMakeLists.txt'
    with open(cmakelists, 'r') as fp:
        contents = fp.read()
    start_idx = contents.find(START_TOKEN) + len(START_TOKEN)
    end_idx = contents[start_idx:].find(END_TOKEN) + len(contents[:start_idx])
    return [str(base_dir / s.strip()) for s in contents[start_idx:end_idx].split() if s.strip() != '']


CLANG_DIR = '/home/nicholas/Documents/llvm-project/clang/'
LLVM_DIR = '/home/nicholas/Documents/llvm-project/llvm/'

_llvm_config_path = pathlib.Path(LLVM_DIR) / 'include/llvm/Config'
_config_dir = pathlib.Path('src/llvm/Config/')
_config_dir.mkdir(exist_ok=True, parents=True)
with open(_config_dir / 'llvm-config.h', 'w') as fp:
    fp.write(_llvm_config(_llvm_config_path))
with open(_config_dir / 'abi-breaking.h', 'w') as fp:
    fp.write(_abi_breaking_config(_llvm_config_path))

_basic_path = pathlib.Path(CLANG_DIR) / 'lib/Basic'
clangBasic_sources = _cmakelists_scrape(
    _basic_path,
    START_TOKEN='add_clang_library(clangBasic',
    END_TOKEN='${version_inc}',
)
clangBasic_include = [
    'src/',
    pathlib.Path(CLANG_DIR) / 'include',
    pathlib.Path(CLANG_DIR) / 'lib/Basic',
    pathlib.Path(LLVM_DIR) / 'include',
]

_lex_path = pathlib.Path(CLANG_DIR) / 'lib/Lex'
clangLex_sources = _cmakelists_scrape(
    _lex_path,
    START_TOKEN='add_clang_library(clangLex',
    END_TOKEN='LINK_LIBS',
)
clangLex_include = [
    'src/',
    pathlib.Path(CLANG_DIR) / 'include',
    pathlib.Path(LLVM_DIR) / 'include',
]

_ast_path = pathlib.Path(CLANG_DIR) / 'lib/AST'
clangAST_sources = _cmakelists_scrape(
    _ast_path,
    START_TOKEN='add_clang_library(clangAST',
    END_TOKEN='LINK_LIBS',
)
clangAST_include = [
    'src/',
    'src/AST/',
    pathlib.Path(CLANG_DIR) / 'include',
    pathlib.Path(LLVM_DIR) / 'include',
]


setup(
    name='cythonator',
    version='0.0.1',
    author='Nicholas McKibben',
    author_email='nicholas.bgp@gmail.com',
    url='https://github.com/mckib2/cythonator',
    license='MIT',
    description='C++ header -> Cython',
    long_description=open('README.rst', encoding='utf-8').read(),
    packages=find_packages(),
    keywords='clang cython',
    install_requires=open('requirements.txt', encoding='utf-8').read().split(),
    python_requires='>=3.5',

    ext_modules=[
        # Extension(
        #     'clangBasic',
        #     sources=clangBasic_sources,
        #     include_dirs=clangBasic_include,
        #     language='c++',
        # ),
        # Extension(
        #     'clangLex',
        #     sources=clangLex_sources,
        #     libraries=['clangBasic'],
        #     include_dirs=clangLex_include,
        #     language='c++',
        # ),
        # Extension(
        #     'clangAST',
        #     sources=clangAST_sources,
        #     libraries=['clangBasic', 'clangLex'],
        #     include_dirs=clangAST_include,
        #     language='c++',
        # ),

        # Build all sources together to avoid linking problems
        Extension(
            'clangAST',
            sources=clangBasic_sources + clangLex_sources + clangAST_sources,
            include_dirs=list(set(clangBasic_include + clangLex_include + clangAST_include)),
            language='c++',
        )
    ],
)
