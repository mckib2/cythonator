'''Compile the clang tools we need.'''

import pathlib
from setuptools import find_packages
from distutils.core import setup

from numpy.distutils.misc_util import Configuration


def _cmakelists_scrape(base_dir, START_TOKEN, END_TOKEN, extra_source_dirs=None):
    cmakelists = base_dir / 'CMakeLists.txt'
    with open(cmakelists, 'r') as fp:
        contents = fp.read()
    start_idx = contents.find(START_TOKEN) + len(START_TOKEN)
    end_idx = contents[start_idx:].find(END_TOKEN) + len(contents[:start_idx])
    sources = [str(base_dir / s.split('#')[0].strip()) for s in contents[start_idx:end_idx].split('\n') if s.strip() != '' and s.strip()[0] != '#']

    # If file doesn't exist, then look elsewhere
    for ii, s in enumerate(sources):
        p = pathlib.Path(s)
        if not p.exists() and extra_source_dirs:
            for d in extra_source_dirs:
                if p.name in [f.name for f in pathlib.Path(d).glob('*')]:
                    sources[ii] = pathlib.Path(d) / p.name
                    break
    return sources


def configuration(parent_package='', top_path=None):
    config = Configuration('', parent_package, top_path)

    CLANG_DIR = pathlib.Path('/home/nicholas/Documents/llvm-project/clang/')
    LLVM_DIR = pathlib.Path('/home/nicholas/Documents/llvm-project/llvm/')

    class lib_t:
        def __init__(self, name, START_TOKEN=None, END_TOKEN=None,
                     extra_library_dirs=[], libraries=[], directory=None,
                     link_libs=[], ignore_libs=(), actual_path=None,
                     cmake_subs=None, extra_source_dirs=None):
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
            self.extra_source_dirs = extra_source_dirs

        def get_sources(self):
            # _path = self.actual_path if self.actual_path is not None else l.name
            sources = _cmakelists_scrape(
                self.directory / 'lib' / self.actual_path,
                START_TOKEN=self.START_TOKEN,
                END_TOKEN=self.END_TOKEN,
                extra_source_dirs=self.extra_source_dirs,
            )
            if self.cmake_subs is not None:
                for key, val in self.cmake_subs.items():
                    sources = [s.replace(key, val).strip() for s in sources]
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
        lib_t('LLVMDemangle'),
        lib_t('LLVMSupport', link_libs=['LLVMDemangle'], libraries=['dl', 'm', 'rt', 'tinfo', 'z'], cmake_subs={'${ALLOCATOR_FILES}': ''}),
        lib_t('LLVMBinaryFormat', link_libs=['LLVMSupport']),
        lib_t('LLVMDebugInfoMSF', link_libs=['LLVMSupport'], actual_path='DebugInfo/MSF'),
        lib_t('LLVMBitstreamReader', link_libs=['LLVMSupport'], actual_path='Bitstream/Reader'),
        lib_t('LLVMDebugInfoCodeView', link_libs=['LLVMDebugInfoMSF', 'LLVMSupport'], actual_path='DebugInfo/CodeView'),
        lib_t('LLVMMC', link_libs=['LLVMSupport', 'LLVMDebugInfoCodeView', 'LLVMBinaryFormat']),
        lib_t('LLVMRemarks', link_libs=['LLVMBitstreamReader', 'LLVMSupport']),
        lib_t('LLVMCore', link_libs=['LLVMBinaryFormat', 'LLVMRemarks'], actual_path='IR'),
        lib_t('LLVMBitReader', link_libs=['LLVMCore', 'LLVMBitstreamReader', 'LLVMSupport'], actual_path='Bitcode/Reader'),
        lib_t('LLVMTextAPI', link_libs=['LLVMSupport', 'LLVMBinaryFormat']),
        lib_t('LLVMMCParser', link_libs=['LLVMSupport', 'LLVMMC'], actual_path='MC/MCParser'),
        lib_t('LLVMObject', link_libs=['LLVMCore', 'LLVMBitReader', 'LLVMSupport', 'LLVMTextAPI',  'LLVMBinaryFormat', 'LLVMMCParser', 'LLVMMC']),
        lib_t('LLVMProfileData', link_libs=['LLVMSupport', 'LLVMCore']),
        lib_t('LLVMAnalysis', link_libs=['LLVMSupport', 'LLVMProfileData', 'LLVMCore', 'LLVMObject', 'LLVMBinaryFormat']),
        lib_t('LLVMTransformUtils', link_libs=['LLVMSupport', 'LLVMCore', 'LLVMAnalysis'], actual_path='Transforms/Utils'),
        lib_t('LLVMFrontendOpenMP', link_libs=['LLVMSupport', 'LLVMTransformUtils', 'LLVMCore'], actual_path='Frontend/OpenMP', extra_source_dirs=['src/Frontend/OpenMP/']),
        lib_t('LLVMOption', link_libs=['LLVMSupport'], libraries=['dl', 'm', 'rt', 'tinfo', 'z']),


        # Clang dependencies
        lib_t('clangBasic', link_libs=['LLVMMC', 'LLVMSupport', 'LLVMCore'], END_TOKEN='${version_inc}', extra_library_dirs=[CLANG_DIR / 'lib/Basic']),
        lib_t('clangLex', link_libs=['LLVMSupport', 'clangBasic']),
        lib_t('clangAST', link_libs=['clangLex', 'clangBasic', 'LLVMBinaryFormat', 'LLVMFrontendOpenMP', 'LLVMCore'], extra_library_dirs=['src/AST']),
        lib_t('clangASTMatchers', link_libs=['LLVMSupport', 'clangLex', 'clangBasic', 'clangAST', 'LLVMFrontendOpenMP']),
        lib_t('clangAnalysis', link_libs=['LLVMSupport', 'clangLex', 'clangASTMatchers', 'clangBasic', 'clangAST', 'LLVMFrontendOpenMP']),
        lib_t('clangEdit', link_libs=['LLVMSupport', 'clangLex', 'clangBasic', 'clangAST']),
        lib_t('clangSema', link_libs=['LLVMSupport', 'clangEdit', 'clangLex', 'clangBasic', 'clangAnalysis', 'clangAST', 'LLVMFrontendOpenMP'], END_TOKEN='DEPENDS', extra_library_dirs=['src/Sema/']),
        lib_t('clangParse', link_libs=['LLVMSupport', 'LLVMMC', 'clangLex', 'clangSema', 'clangBasic', 'LLVMMCParser', 'clangAST', 'LLVMFrontendOpenMP']),
        lib_t('clangSerialization', link_libs=['clangBasic', 'clangLex', 'clangSema', 'clangAST', 'LLVMBitReader', 'LLVMBitstreamReader', 'LLVMSupport'], END_TOKEN='ADDITIONAL_HEADERS', extra_library_dirs=[CLANG_DIR / 'lib/Serialization']),
        lib_t('clangDriver', link_libs=['LLVMSupport', 'LLVMOption', 'clangBasic', 'LLVMBinaryFormat', 'LLVMProfileData'], END_TOKEN='DEPENDS', extra_library_dirs=[CLANG_DIR / 'lib/Driver']),
        lib_t('clangFrontend', link_libs=['LLVMBitReader', 'LLVMBitstreamReader', 'LLVMOption', 'LLVMProfileData', 'LLVMSupport', 'clangAST', 'clangBasic', 'clangDriver', 'clangEdit', 'clangLex', 'clangParse', 'clangSema', 'clangSerialization'], END_TOKEN='DEPENDS'),
        lib_t('clangRewrite', link_libs=['LLVMSupport', 'clangBasic', 'clangLex']),
        lib_t('clangToolingCore', link_libs=['LLVMSupport', 'clangAST', 'clangBasic', 'clangLex', 'clangRewrite'], actual_path='Tooling/Core'),
        lib_t('clangToolingInclusions', link_libs=['LLVMSupport', 'clangBasic', 'clangLex', 'clangRewrite', 'clangToolingCore'], actual_path='Tooling/Inclusions'),
        lib_t('clangFormat', link_libs=['LLVMSupport', 'clangBasic', 'clangLex', 'clangToolingCore', 'clangToolingInclusions']),
        lib_t('clangTooling', link_libs=['LLVMFrontendOpenMP', 'LLVMOption', 'LLVMSupport', 'clangAST', 'clangASTMatchers', 'clangBasic', 'clangDriver', 'clangFormat', 'clangFrontend', 'clangLex', 'clangRewrite', 'clangSerialization', 'clangToolingCore'], END_TOKEN='DEPENDS'),
        lib_t('clangRewriteFrontend', link_libs=['LLVMSupport', 'clangBasic', 'clangLex'], actual_path='Frontend/Rewrite')

        # We are currently missing symbol: undefined symbol: _ZTIN4llvm21PrettyStackTraceEntryE

        # Additional LLVM dependencies for clangCodeGen
        # lib_t('LLVMAggressiveInstCombine'),
        # lib_t('LLVMBitWriter'),
        # lib_t('LLVMCoroutines'),
        # lib_t('LLVMCoverage'),
        # lib_t('LLVMExtensions'),
        # lib_t('LLVMIRReader'),
        # lib_t('LLVMInstCombine'),
        # lib_t('LLVMInstrumentation'),
        # lib_t('LLVMLTO'),
        # lib_t('LLVMLinker'),
        # lib_t('LLVMObjCARCOpts'),
        # lib_t('LLVMPasses'),
        # lib_t('LLVMRemarks'),
        # lib_t('LLVMScalarOpts'),
        # lib_t('LLVMTarget'),
        # lib_t('LLVMTransformUtils'),
        # lib_t('LLVMipo'),

        # # Additional dependencies of clang-interpreter
        # lib_t('LLVMExecutionEngine'),
        # lib_t('LLVMMCJIT'),
        # lib_t('LLVMOrcJIT'),
        # lib_t('LLVMRuntimeDyld'),
        # lib_t('LLVMX86AsmParser'),
        # lib_t('LLVMX86CodeGen'),
        # lib_t('LLVMX86Desc'),
        # lib_t('LLVMX86Disassembler'),
        # lib_t('LLVMX86Info'),
        # lib_t('clangCodeGen', link_libs=['LLVMAggressiveInstCombine', 'LLVMAnalysis', 'LLVMBitReader', 'LLVMBitWriter', 'LLVMCore', 'LLVMCoroutines', 'LLVMCoverage', 'LLVMExtensions', 'LLVMFrontendOpenMP', 'LLVMIRReader', 'LLVMInstCombine', 'LLVMInstrumentation', 'LLVMLTO', 'LLVMLinker', 'LLVMMC', 'LLVMObjCARCOpts', 'LLVMObject', 'LLVMPasses', 'LLVMProfileData', 'LLVMRemarks', 'LLVMScalarOpts', 'LLVMSupport', 'LLVMTarget', 'LLVMTransformUtils', 'LLVMipo', 'clangAST', 'clangASTMatchers', 'clangAnalysis', 'clangBasic', 'clangFrontend', 'clangLex', 'clangSerialization']),
    ]

    for l in libs:
        config.add_library(
            l.name,
            sources=l.get_sources(),
            include_dirs=l.get_includes(),
            libraries=l.libraries + l.link_libs,
            language='c++',
            cflags=[
                '-Wno-strict-aliasing',
                '-Wno-maybe-uninitialized',
                '-Wno-comment',
                '-Wnoexcept-type',
            ],
            macros=[
                ('LLVM_ENABLE_ABI_BREAKING_CHECKS', 0),
                ('HAVE_SYSEXITS_H', 1),
            ],)
    #     if l.link_libs:
    #         setattr(ext, 'clang_link', l.link_libs)

    # # Build all together
    # config.add_extension(
    #     'clang',
    #     sources=set(chain.from_iterable([l.get_sources() for l in libs])),
    #     include_dirs=set(chain.from_iterable([l.get_includes() for l in libs])),
    #     libraries=set(chain.from_iterable([l.libraries for l in libs])),
    #     language='c++',
    #     extra_compile_args=[
    #         '-Wno-strict-aliasing',
    #         '-Wno-maybe-uninitialized',
    #         '-Wno-comment',
    #         '-Wnoexcept-type',
    #     ],
    #     define_macros=[
    #         ('LLVM_ENABLE_ABI_BREAKING_CHECKS', 0),
    #         ('HAVE_SYSEXITS_H', 1),
    #     ],
    # )

    # Build something that uses the libraries to make sure it worked
    config.add_extension(
        'tests.build_test',
        sources=[
            'tests/build_test.pyx',
            'tests/clang-tool.cpp',
            # 'tests/simple.cpp',
            # 'tests/main.cpp',  # my modified version
            # CLANG_DIR / 'examples/clang-interpreter/main.cpp',
        ],
        include_dirs=[
            'src/',
            CLANG_DIR / 'include',
            LLVM_DIR / 'include',
        ],
        libraries=[l.name for l in libs[::-1]] + ['dl', 'm', 'rt', 'tinfo', 'z'],
        language='c++',
        extra_compile_args=['-fpermissive'],
        # extra_link_args=['-Wl,-z,defs'],
    )

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
)
