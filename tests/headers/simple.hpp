void void_function_void();
void* void_star_function_void();
const void* const_void_star_function_void();

unsigned short int unsigned_short_int_function_void();
unsigned short int& unsigned_short_int_ref_function_void();

template<typename T>
int templated_int_function(T& t);

void void_function_int(int a);
void void_function_int_ref(int&);

namespace ns {
  void void_ns_function();
}

typedef int& myInt;
typedef myInt otherInt;
typedef otherInt distantInt;

struct myStruct {
  myStruct() {}
  void* method1(int& namedparam);
  int intField;
  double* dblField;
};

class myClass {
  int intField;
public:
  double* dblField;
  template<class T> myStruct* tfun(T& t);
};

template<typename U>
class TemplatedClass {
 public:
  myClass* tfun(U* u);
};

namespace ns {
  template<class V>
  struct TemplatedStruct {
    myStruct* tfun(V& v);
  };
}
