
namespace one {
  namespace two {

    class MyClass {
    public:
      MyClass() { }
      ~MyClass() { }
      int myfunction (double, long long myLongLong) {}
      virtual int my_virt_function (const double) {}
      int* myCoolFunction(double*) const {}
      const int& myOtherCoolFunction(double& namedArg) {}
      int * myTrickyFunction(double constArg, int argConst) {}
    private:
      int myprop;
      int* myprop_star;
    };

  }
}
