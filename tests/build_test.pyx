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


# cdef extern from "main.hpp" nogil:
#     int mymain(int argc, const char **argv)

cdef extern from "Python.h":
    char* PyUnicode_AsUTF8(object unicode)

from libc.stdlib cimport malloc, free
from libc.string cimport strcmp

cdef char ** to_cstring_array(list_str):
    cdef char **ret = <char **>malloc(len(list_str) * sizeof(char *))
    for i in xrange(len(list_str)):
        ret[i] = PyUnicode_AsUTF8(list_str[i])
    return ret

# def test_clang_interpreter(int argc, args):
#     cdef char **argv = to_cstring_array(args)
#     cdef int res = mymain(argc, argv)
#     free(argv)
#     return res

cdef extern from "simple.hpp" nogil:
    int simple(int argc, const char ** argv)

def test_simple(int argc, args):
    cdef char **argv = to_cstring_array(args)
    cdef int res = simple(argc, argv)
    free(argv)
    return res
