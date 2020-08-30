'''Run tests on build to make sure llvm/clang is good.'''

from build_test import test_clangBasic

assert test_clangBasic()
