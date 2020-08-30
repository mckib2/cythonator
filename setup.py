'''Compile the clang tools we need.'''

import pathlib
import platform
import re
from itertools import chain
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
            print(ext.name)
            if hasattr(ext, 'clang_link'):

                # We need 'lib' versions of the shared libraries
                # that need to be linked
                build_lib = pathlib.Path(self.build_lib) / 'cythonator'
                so_to_link = [self.get_ext_filename(l) for l in ext.clang_link]
                to_link = []
                for l in so_to_link:
                    libpath = pathlib.Path(l)
                    stem = l[:-len(''.join(libpath.suffixes))]
                    to_move = pathlib.Path(
                        self.compiler.library_filename(stem)).with_suffix(libpath.suffix)
                    self.copy_file(build_lib / l, build_lib / to_move)
                    to_link.append(str(stem))

                # Link 'lib' versions to the object files of each extension
                self.compiler.link_shared_lib(
                    self.compiler.object_filenames([
                        self.build_temp + '/' + s for s in ext.sources]),
                    ext.name,
                    libraries=ext.libraries + to_link,
                    library_dirs=[str(build_lib)],
                    runtime_library_dirs=['.'],
                )


def _cmakelists_scrape(base_dir, START_TOKEN, END_TOKEN):
    cmakelists = base_dir / 'CMakeLists.txt'
    with open(cmakelists, 'r') as fp:
        contents = fp.read()
    start_idx = contents.find(START_TOKEN) + len(START_TOKEN)
    end_idx = contents[start_idx:].find(END_TOKEN) + len(contents[:start_idx])
    return [str(base_dir / s.split('#')[0].strip()) for s in contents[start_idx:end_idx].split('\n') if s.strip() != '' and s.strip()[0] != '#']


def configuration(parent_package='', top_path=None):

    config = Configuration('cythonator', parent_package, top_path)

    # TODO: we may need to be compiling some LLVM and linking as well...

    # lib_t = namedtuple(
    #     'lib_t',
    #     'name START_TOKEN END_TOKEN extra_library_dirs llvm_libs clang_libs actual_path')
    CLANG_DIR = pathlib.Path('/home/nicholas/Documents/llvm-project/clang/')
    LLVM_DIR = pathlib.Path('/home/nicholas/Documents/llvm-project/llvm/')

    class lib_t:
        def __init__(self, name, START_TOKEN=None, END_TOKEN=None,
                     extra_library_dirs=[], libraries=(), directory=None,
                     link_libs=(), ignore_libs=(), actual_path=None,
                     cmake_subs=None):
            self.name = name
            if START_TOKEN is None:
                if 'LLVM' in name:
                    self.START_TOKEN = 'add_llvm_component_library(' + name
                elif 'clang' in name:
                    self.START_TOKEN = 'add_clang_library(' + name
            else:
                self.START_TOKEN = START_TOKEN
            if END_TOKEN is None:
                if 'LLVM' in name:
                    self.END_TOKEN = 'ADDITIONAL_HEADER_DIRS'
                elif 'clang' in name:
                    self.END_TOKEN = 'LINK_LIBS'
            else:
                self.END_TOKEN = END_TOKEN
            self.extra_library_dirs = extra_library_dirs
            self.libraries = libraries
            self.directory = LLVM_DIR if 'LLVM' in name else CLANG_DIR
            self.link_libs = link_libs
            self.ignore_libs = ignore_libs
            if actual_path is None:
                if 'LLVM' in name:
                    self.actual_path = name[len('LLVM'):]
                elif 'clang' in name:
                    self.actual_path = name[len('clang'):]
            else:
                self.actual_path = actual_path
            self.cmake_subs = cmake_subs

        def get_sources(self):
            # _path = self.actual_path if self.actual_path is not None else l.name
            sources = _cmakelists_scrape(
                self.directory / 'lib' / self.actual_path,
                START_TOKEN=self.START_TOKEN,
                END_TOKEN=self.END_TOKEN,
            )
            if self.cmake_subs is not None:
                for key, val in self.cmake_subs.items():
                    sources = [s.replace(key, val).strip() for s in sources]
            # print(sources)
            return [s for s in sources if pathlib.Path(s).suffix]

        def get_includes(self):
            includes = [
                'src/',
                CLANG_DIR / 'include',
                LLVM_DIR / 'include',
            ] + self.extra_library_dirs
            return includes

    libs = [

        # LLVM dependencies
        lib_t(name='LLVMDemangle'),
        lib_t(name='LLVMSupport',
              link_libs=['LLVMDemangle'],
              libraries=['dl', 'm', 'rt', 'tinfo'],
              cmake_subs={'${ALLOCATOR_FILES}': ''}),
        lib_t(name='LLVMMC',
              link_libs=['LLVMSupport', 'LLVMDebugInfoCodeView',
                         'LLVMBinaryFormat']),
        lib_t(name='LLVMDebugInfoMSF',
              link_libs=['LLVMSupport'],
              actual_path='DebugInfo/MSF'),
        lib_t(name='LLVMDebugInfoCodeView',
              link_libs=['LLVMDebugInfoMSF', 'LLVMSupport'],
              actual_path='DebugInfo/CodeView'),
        lib_t(name='LLVMBinaryFormat',
              link_libs=['LLVMSupport']),
        lib_t(name='LLVMCore',
              link_libs=['LLVMBinaryFormat', 'LLVMRemarks'],
              actual_path='IR'),
        lib_t(name='LLVMRemarks',
              link_libs=['LLVMBitstreamReader', 'LLVMSupport']),
        lib_t(name='LLVMBitstreamReader',
              link_libs=['LLVMSupport'],
              actual_path='Bitstream/Reader'),
        lib_t(name='LLVMBitReader',
              link_libs=['LLVMCore', 'LLVMBitstreamReader', 'LLVMSupport'],
              actual_path='Bitcode/Reader'),
        lib_t(name='LLVMTextAPI',
              link_libs=['LLVMSupport', 'LLVMBinaryFormat']),
        lib_t(name='LLVMMCParser',
              link_libs=['LLVMSupport', 'LLVMMC'],
              actual_path='MC/MCParser'),
        lib_t(name='LLVMObject',
              link_libs=['LLVMCore', 'LLVMBitReader', 'LLVMSupport',
                         'LLVMTextAPI',  'LLVMBinaryFormat', 'LLVMMCParser',
                         'LLVMMC']),
        lib_t(name='LLVMProfileData',
              link_libs=['LLVMSupport', 'LLVMCore']),
        lib_t(name='LLVMAnalysis',
              link_libs=['LLVMSupport', 'LLVMProfileData', 'LLVMCore',
                         'LLVMObject', 'LLVMBinaryFormat']),
        lib_t(name='LLVMTransformUtils',
              link_libs=['LLVMSupport', 'LLVMCore', 'LLVMAnalysis'],
              actual_path='Transforms/Utils'),
        lib_t(name='LLVMFrontendOpenMP',
              link_libs=['LLVMSupport', 'LLVMTransformUtils', 'LLVMCore'],
              actual_path='Frontend/OpenMP'),

        # Clang dependencies
        lib_t(name='clangBasic', END_TOKEN='${version_inc}',
              extra_library_dirs=[CLANG_DIR / 'lib/Basic'],
              link_libs=['LLVMMC', 'LLVMSupport', 'LLVMCore']),
        lib_t(name='clangLex',
              link_libs=['LLVMSupport', 'clangBasic']),
        lib_t(name='clangAST',
              link_libs=['clangLex', 'clangBasic', 'LLVMBinaryFormat',
                         'LLVMFrontendOpenMP', 'LLVMCore']),
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

    # for l in libs:
    #     ext = config.add_extension(
    #         l.name,
    #         sources=l.get_sources(),
    #         include_dirs=l.get_includes(),
    #         libraries=l.libraries,
    #         language='c++',
    #         extra_compile_args=['-Wno-strict-aliasing',
    #                             '-Wno-maybe-uninitialized',
    #                             '-Wno-comment',
    #                             ],
    #         define_macros=[
    #             ('LLVM_ENABLE_ABI_BREAKING_CHECKS', 0),
    #             ('HAVE_SYSEXITS_H', 1),
    #         ],)
    #     if l.link_libs:
    #         setattr(ext, 'clang_link', l.link_libs)

    # Build all together
    config.add_extension(
        'clang',
        sources=set(chain.from_iterable([l.get_sources() for l in libs])),
        include_dirs=set(chain.from_iterable([l.get_includes() for l in libs])),
        libraries=set(chain.from_iterable([l.libraries for l in libs])),
        language='c++',
        extra_compile_args=[
            '-Wno-strict-aliasing',
            '-Wno-maybe-uninitialized',
            '-Wno-comment',
            '-Wnoexcept-type',
        ],
        define_macros=[
            ('LLVM_ENABLE_ABI_BREAKING_CHECKS', 0),
            ('HAVE_SYSEXITS_H', 1),
        ],
    )

    # Build something that uses the libraries to make sure it worked
    import subprocess
    subprocess.run(f'g++ -c -I./src/ -I{CLANG_DIR / "include"} -I{LLVM_DIR / "include"} test.cpp -o test.o'.split())
    subprocess.run('g++ test.o -Wl,-rpath -Wl,. -L. -l:clang.cpython-36m-x86_64-linux-gnu.so -lz'.split())

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
