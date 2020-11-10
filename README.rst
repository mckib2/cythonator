Cythonator
==========

THIS PROJECT IS A WORK-IN-PROGRESS

The goal is to use the LLVM/Clang parser and AST tooling to parse a C++ header file and transform the resulting AST into Cython wrappers.  I've created a similar tool using Doxygen's parser and XML output tools in the past but it chokes on modern C++ features, heavy templating, and macro usage.

The tool is made to be as friendly as possible:

    python -m cythonator --header my/header/file.hpp --output my/cython/file.pyx

This will produce a compilable PYX file auto-magically generated from the definitions in the C++ header file.

I'm slowly gathering a pool of test cases.  Most breakage I find is due to templates and meta-programming -- mostly Cython not having infrastructure to handle it.

LLVM/Clang
==========

The necessary headers/libraries are convienently packaged by `clangTooling <https://github.com/mckib2/clangTooling>` (also a WIP).
