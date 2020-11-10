'''Compile the clang tools we need.'''

import pathlib
from setuptools import find_packages
from distutils.core import setup, Extension

from clangTooling import (
    clang_includes,
    llvm_includes,
    library_dir,
    llvm_library_list,
)
from clangTooling.lib import clang_library_list


setup(
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
        Extension(
            'transpiler',
            sources=['src/transpiler.cpp'],
            include_dirs=clang_includes() + llvm_includes(),
            library_dirs=[str(library_dir())],
            libraries=clang_library_list() + llvm_library_list() + ['z', 'curses'],
            language='c++',
            extra_compile_args=['-fno-exceptions', '-fno-rtti'],
            extra_link_args=[],
            define_macros=[
                ('_GNU_SOURCE', None),
                ('__STDC_CONSTANT_MACROS', None),
                ('__STDC_FORMAT_MACROS', None),
                ('__STDC_LIMIT_MACROS', None),
                ('_GLIBCXX_USE_CXX11_ABI', '0'),
            ],
        )
    ],
)
