# distutils: language=c++
# cython: language_level=3

cdef extern from "clang/Basic/LangOptions.h" namespace "clang" nogil:
    cdef cppclass FPOptionsOverride:
        FPOptionsOverride() except +
        void dump()

def test_clangBasic():
    cdef FPOptionsOverride myOverride = FPOptionsOverride()
    myOverride.dump()
    return True
