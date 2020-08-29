'''Compile the clang tools we need.'''

import pathlib
import platform
import re
from collections import namedtuple
from setuptools import find_packages
from distutils.core import Extension, setup
from distutils.command.build_ext import build_ext as _build_ext

from numpy.distutils.misc_util import Configuration


class build_ext(_build_ext):
    def run(self):
        super().run()

        # All the shared library extensions are now built;
        # We need to link all the shared objects together
        for ext in self.extensions:
            if hasattr(ext, 'clang_link') and hasattr(ext, 'llvm_link'):

                # We need 'lib' versions of the shared libraries
                # that need to be linked
                build_lib = pathlib.Path(self.build_lib) / 'cythonator'
                so_to_link = ([self.get_ext_filename('clang' + l) for l in ext.clang_link] +
                              [self.get_ext_filename('LLVM' + l) for l in ext.llvm_link])
                to_link = []
                for l in so_to_link:
                    libpath = pathlib.Path(l)
                    stem = l[:-len(''.join(libpath.suffixes))]
                    to_move = pathlib.Path(
                        self.compiler.library_filename(stem)).with_suffix(libpath.suffix)
                    self.copy_file(build_lib / l, build_lib / to_move)
                    to_link.append(str(stem))

                # Link 'lib' versions to the object files of each extension
                print(to_link)
                self.compiler.link_shared_lib(
                    self.compiler.object_filenames([
                        self.build_temp + '/' + s for s in ext.sources]),
                    ext.name,
                    libraries=to_link,
                    library_dirs=[str(build_lib)],
                    runtime_library_dirs=['.'],
                )


def _cmakelists_scrape(base_dir, START_TOKEN, END_TOKEN):
    cmakelists = base_dir / 'CMakeLists.txt'
    with open(cmakelists, 'r') as fp:
        contents = fp.read()
    start_idx = contents.find(START_TOKEN) + len(START_TOKEN)
    end_idx = contents[start_idx:].find(END_TOKEN) + len(contents[:start_idx])
    return [str(base_dir / s.strip()) for s in contents[start_idx:end_idx].split('\n') if s.strip() != '' and s.strip()[0] != '#']


def configuration(parent_package='', top_path=None):

    config = Configuration('cythonator', parent_package, top_path)

    # TODO: we may need to be compiling some LLVM and linking as well...

    lib_t = namedtuple(
        'lib_t',
        'name START_TOKEN END_TOKEN extra_library_dirs llvm_libs clang_libs actual_path')
    llvm_t = namedtuple('llvm_t', 'name START_TOKEN END_TOKEN link_libs')
    sources = dict()
    includes = dict()
    CLANG_DIR = pathlib.Path('/home/nicholas/Documents/llvm-project/clang/')
    LLVM_DIR = pathlib.Path('/home/nicholas/Documents/llvm-project/llvm/')
    libs = [

        # LLVM dependencies
        llvm_t('MC', None, None, []),
        llvm_t('Support', None, None, []),

        # Clang
        lib_t('Basic', None, '${version_inc}', [CLANG_DIR / 'lib/Basic'],
              ['MC', 'Support'], [], None),
        # lib_t('Lex', None, None, [],
        #       ['Basic'], None),
        # lib_t('AST', None, None, ['src/AST/'],
        #       ['Basic',
        #        'Lex'], None),
        # lib_t('ASTMatchers', None, None, [],
        #       ['Basic',
        #        'Lex',
        #        'AST'], None),
        # lib_t('Analysis', None, None, [],
        #       ['Basic',
        #        'Lex',
        #        'AST',
        #        'ASTMatchers'], None),
        # lib_t('Edit', None, None, [],
        #       ['Basic',
        #        'Lex',
        #        'AST'], None),
        # lib_t('Sema', None, 'DEPENDS', ['src/Sema/'],
        #       ['Basic',
        #        'Lex',
        #        'AST',
        #        'Analysis',
        #        'Edit'], None),
        # lib_t('Parse', None, None, [],
        #       ['Basic',
        #        'Lex',
        #        'AST',
        #        'Sema'], None),
        # lib_t('Serialization', None, 'ADDITIONAL_HEADERS',
        #       [CLANG_DIR / 'lib/Serialization'],
        #       ['Basic',
        #        'Lex',
        #        'AST',
        #        'Sema'], None),
        # lib_t('Driver', None, 'DEPENDS', [CLANG_DIR / 'lib/Driver'],
        #       ['Basic'], None),
        # lib_t('Frontend', None, 'DEPENDS', [],
        #       ['Basic',
        #        'Lex',
        #        'AST',
        #        'Sema',
        #        'Edit',
        #        'Parse',
        #        'Driver',
        #        'Serialization'], None),
        # lib_t('Rewrite', None, None, [], ['Basic', 'Lex'], None),
        # lib_t('ToolingCore', None, None, [],
        #       ['AST',
        #        'Basic',
        #        'Lex',
        #        'Rewrite'], 'Tooling/Core'),
        # lib_t('ToolingInclusions', None, None, [],
        #       ['Basic',
        #        'Lex',
        #        'Rewrite',
        #        'ToolingCore'], 'Tooling/Inclusions'),
        # lib_t('Format', None, None, [],
        #       ['Basic',
        #        'Lex',
        #        'ToolingCore',
        #        'ToolingInclusions'], None),
        # lib_t('Tooling', None, 'DEPENDS', [],
        #       ['AST',
        #        'ASTMatchers',
        #        'Basic',
        #        'Driver',
        #        'Format',
        #        'Frontend',
        #        'Lex',
        #        'Rewrite',
        #        'Serialization',
        #        'ToolingCore'], None),
    ]

    for l in libs:

        if isinstance(l, lib_t):
            if l.START_TOKEN is None:
                START_TOKEN = 'add_clang_library(clang' + l.name
            else:
                START_TOKEN = l.START_TOKEN
            if l.END_TOKEN is None:
                END_TOKEN = 'LINK_LIBS'
            else:
                END_TOKEN = l.END_TOKEN

            _path = l.actual_path if l.actual_path is not None else l.name
            sources[l.name] = _cmakelists_scrape(
                pathlib.Path(CLANG_DIR) / 'lib' / _path,
                START_TOKEN=START_TOKEN,
                END_TOKEN=END_TOKEN,
            )
            includes[l.name] = [
                'src/',
                CLANG_DIR / 'include',
                LLVM_DIR / 'include',
            ] + l.extra_library_dirs
        else:
            if l.START_TOKEN is None:
                START_TOKEN = 'add_llvm_component_library(LLVM' + l.name
            else:
                START_TOKEN = l.START_TOKEN
            if l.END_TOKEN is None:
                END_TOKEN = 'ADDITIONAL_HEADER_DIRS'
            else:
                END_TOKEN = l.END_TOKEN

            sources[l.name] = _cmakelists_scrape(
                pathlib.Path(LLVM_DIR) / 'lib' / l.name,
                START_TOKEN=START_TOKEN,
                END_TOKEN=END_TOKEN,
            )
            includes[l.name] = [
                'src/',
                LLVM_DIR / 'include',
            ] # + l.extra_library_dirs

        prefix = 'clang' if isinstance(l, lib_t) else 'LLVM'
        ext = config.add_extension(
            prefix + l.name,
            sources=sources[l.name],
            include_dirs=includes[l.name],
            language='c++',
            extra_compile_args=['-Wno-strict-aliasing',
                                '-Wno-maybe-uninitialized',
                                '-Wno-comment',
                                ],
            define_macros=[
                ('LLVM_DISABLE_ABI_BREAKING_CHECKS_ENFORCING', 1),
            ],)
        if isinstance(l, lib_t):
            setattr(ext, 'llvm_link', l.llvm_libs)
            setattr(ext, 'clang_link', l.clang_libs)

    return config


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
    **configuration(top_path='').todict(),
    cmdclass={'build_ext': build_ext},
)
