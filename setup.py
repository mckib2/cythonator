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
            if ext.clang_link:

                # We need 'lib' versions of the shared libraries
                # that need to be linked
                build_lib = pathlib.Path(self.build_lib) / 'cythonator'
                so_to_link = [self.get_ext_filename('clang' + l) for l in ext.clang_link]
                to_link = []
                for ii, l in enumerate(ext.clang_link):
                    to_move = pathlib.Path(
                        self.compiler.library_filename('clang' + l)).with_suffix(
                            pathlib.Path(so_to_link[ii]).suffix)
                    to_link0 = 'clang' + l
                    self.copy_file(build_lib / so_to_link[ii], build_lib / to_move)
                    to_link.append(str(to_link0))

                # Link 'lib' versions to the object files of each extension
                self.compiler.link_shared_lib(
                    self.compiler.object_filenames([
                        self.build_temp + '/' + s for s in ext.sources]),
                    ext.name,
                    libraries=to_link,
                    library_dirs=[str(build_lib)],
                )


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


LLVM_DIR = pathlib.Path('/home/nicholas/Documents/llvm-project/llvm/')
_llvm_config_path = LLVM_DIR / 'include/llvm/Config'
_config_dir = pathlib.Path('src/llvm/Config/')
_config_dir.mkdir(exist_ok=True, parents=True)
with open(_config_dir / 'llvm-config.h', 'w') as fp:
    fp.write(_llvm_config(_llvm_config_path))
with open(_config_dir / 'abi-breaking.h', 'w') as fp:
    fp.write(_abi_breaking_config(_llvm_config_path))


def configuration(parent_package='', top_path=None):

    config = Configuration('cythonator', parent_package, top_path)

    # TODO: we may need to be compiling some LLVM and linking as well...

    lib_t = namedtuple(
        'lib_t',
        'name START_TOKEN END_TOKEN extra_library_dirs link_libs actual_path')
    clang_sources = dict()
    clang_includes = dict()
    CLANG_DIR = pathlib.Path('/home/nicholas/Documents/llvm-project/clang/')
    libs = [
        lib_t('Basic', None, '${version_inc}', [CLANG_DIR / 'lib/Basic'],
              [], None),
        lib_t('Lex', None, None, [], ['Basic'], None),
        lib_t('AST', None, None, ['src/AST/'],
              ['Basic',
               'Lex'], None),
        lib_t('ASTMatchers', None, None, [],
              ['Basic',
               'Lex',
               'AST'], None),
        lib_t('Analysis', None, None, [],
              ['Basic',
               'Lex',
               'AST',
               'ASTMatchers'], None),
        lib_t('Edit', None, None, [],
              ['Basic',
               'Lex',
               'AST'], None),
        lib_t('Sema', None, 'DEPENDS', ['src/Sema/'],
              ['Basic',
               'Lex',
               'AST',
               'Analysis',
               'Edit'], None),
        lib_t('Parse', None, None, [],
              ['Basic',
               'Lex',
               'AST',
               'Sema'], None),
        lib_t('Serialization', None, 'ADDITIONAL_HEADERS',
              [CLANG_DIR / 'lib/Serialization'],
              ['Basic',
               'Lex',
               'AST',
               'Sema'], None),
        lib_t('Driver', None, 'DEPENDS', [CLANG_DIR / 'lib/Driver'],
              ['Basic'], None),
        lib_t('Frontend', None, 'DEPENDS', [],
              ['Basic',
               'Lex',
               'AST',
               'Sema',
               'Edit',
               'Parse',
               'Driver',
               'Serialization'], None),
        lib_t('Rewrite', None, None, [], ['Basic', 'Lex'], None),
        lib_t('ToolingCore', None, None, [],
              ['AST',
               'Basic',
               'Lex',
               'Rewrite'], 'Tooling/Core'),
        lib_t('ToolingInclusions', None, None, [],
              ['Basic',
               'Lex',
               'Rewrite',
               'ToolingCore'], 'Tooling/Inclusions'),
        lib_t('Format', None, None, [],
              ['Basic',
               'Lex',
               'ToolingCore',
               'ToolingInclusions'], None),
        lib_t('Tooling', None, 'DEPENDS', [],
              ['AST',
               'ASTMatchers',
               'Basic',
               'Driver',
               'Format',
               'Frontend',
               'Lex',
               'Rewrite',
               'Serialization',
               'ToolingCore'], None),
    ]

    for l in libs:
        if l.START_TOKEN is None:
            START_TOKEN = 'add_clang_library(clang' + l.name
        else:
            START_TOKEN = l.START_TOKEN
        if l.END_TOKEN is None:
            END_TOKEN = 'LINK_LIBS'
        else:
            END_TOKEN = l.END_TOKEN

        _path = l.actual_path if l.actual_path is not None else l.name
        clang_sources[l.name] = _cmakelists_scrape(
            pathlib.Path(CLANG_DIR) / 'lib' / _path,
            START_TOKEN=START_TOKEN,
            END_TOKEN=END_TOKEN,
        )
        clang_includes[l.name] = [
            'src/',
            CLANG_DIR / 'include',
            LLVM_DIR / 'include',
        ] + l.extra_library_dirs

        ext = config.add_extension(
            'clang' + l.name,
            sources=clang_sources[l.name],
            include_dirs=clang_includes[l.name],
            language='c++',
            extra_compile_args=['-Wno-strict-aliasing',
                                '-Wno-maybe-uninitialized',
                                '-Wno-comment',
                                ])
        setattr(ext, 'clang_link', l.link_libs)

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
