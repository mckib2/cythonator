'''Run tests on build to make sure llvm/clang is good.'''

# from build_test import test_clangBasic

# assert test_clangBasic()

# from build_test import test_clang_interpreter

# print(test_clang_interpreter(1, 'main.exe'))

from build_test import test_simple

test_simple(['myTool', '--ast-dump', 'tests/simple.hpp'])
