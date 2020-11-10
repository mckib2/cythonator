#include "clang/AST/ASTConsumer.h"
#include "clang/AST/RecursiveASTVisitor.h"
#include "clang/Frontend/CompilerInstance.h"
#include "clang/Frontend/FrontendAction.h"
#include "clang/Tooling/Tooling.h"
#include "llvm/IR/DerivedTypes.h"

#include <sstream>
#include <fstream>
#include <iostream>
#include <set>

using namespace clang;

class CythonVisitor : public RecursiveASTVisitor<CythonVisitor> {
public:
  explicit CythonVisitor(ASTContext *Context, const char* header_file)
    : Context(Context)
    , tab_lvl(0)
    , header_file(header_file)
  {}

  std::string tab() {
    std::ostringstream tabber;
    for (auto ii = 0; ii < tab_lvl; ++ii) {
      tabber << "    ";
    }
    return tabber.str();
  }

  std::string typer(const clang::QualType & t) {

    // replace _Bool with bool and add to cimports
    // TODO: there's got to be a better way to do this...
    auto idx = t.getAsString().find("_Bool");
    if (idx != std::string::npos) {
      if (!done_cimports.count("bool")) {
        done_cimports.insert("bool");
        cimports << "from libcpp cimport bool" << "\n";
      }
      return t.getAsString().replace(idx, 5, "bool");
    }

    return t.getAsString();
  }

  bool VisitFunctionDecl(FunctionDecl *Declaration) {

    decls << "cdef extern \"" << header_file << "\" nogil:" << "\n";
    ++tab_lvl;
    decls << tab() << typer(Declaration->getReturnType()) << " "
          << Declaration->getNameAsString() << "(";

    std::size_t ii = 0; // iteration number
    for (auto it = Declaration->param_begin(); it != Declaration->param_end(); ++it) {
      decls << typer((*it)->getOriginalType()) << " ";
      if ((*it)->getNameAsString() != "") {
        // Use the parameter's name if we have it
        decls << (*it)->getNameAsString();
      }
      else {
        decls << "param" << ii;
      }
      if ((it+1) != Declaration->param_end()) {
        decls << ", ";
      }
      ++ii;
    }
    decls << ")" << "\n";
    --tab_lvl;
    return true;
  }

  bool VisitCXXRecordDecl(CXXRecordDecl *Declaration) {
    return true;
  }

  void HandleStruct(CXXRecordDecl *Declaration, const std::string & name) {
    // forward_decls << "class " << name << "(ctypes.Structure):" << "\n"
    //               << "    pass" << "\n";

    // if (Declaration->field_empty()) {
    //   global_decls << name << "._fields_ = []\n\n";
    // }
    // else {
    //   global_decls << name << "._fields_ = [" << "\n";
    //   for (const auto & f : Declaration->fields()) {
    //     global_decls << "    ('" << f->getNameAsString() << "', " << typemap(f->getType()) << " " << "),\n";
    //   }
    //   global_decls << "]\n\n";
    // }
  }

  bool VisitTypedefNameDecl(TypedefNameDecl *Declaration) {
    if (auto a = llvm::dyn_cast<clang::ElaboratedType>(Declaration->getUnderlyingType())) {
      if (a->isStructureType()) {
        if (auto d = llvm::dyn_cast_or_null<clang::CXXRecordDecl>(a->getAsStructureType()->getDecl())) {
          if (d->getNameAsString() != "") {
            HandleStruct(d, d->getNameAsString());
          }
          else {
            HandleStruct(d, a->getNamedType().getAsString());
          }
        }
      }
    }
    return true;
  }

  void toString(const char *const outfile) {
    std::ofstream myfile;
    myfile.open(outfile);
    myfile << "# NOTE: This file was autogenerated using cythonator." << "\n"
           << "#       Any changes will be overwritten upon regeneration." << "\n"
           << "\n";

    myfile << "\n"
           << cimports.str()
           << "\n"
           << decls.str();
    myfile.close();
  }

private:
  ASTContext *Context;
  std::ostringstream decls;
  std::ostringstream cimports;
  std::set<std::string> done_cimports;
  int tab_lvl;
  const char* header_file;
};

class TranspilationConsumer : public clang::ASTConsumer {
public:
  explicit TranspilationConsumer(ASTContext *Context, const char* header_file, const char* outfile)
    : Visitor(Context, header_file), outfile(outfile) {}

  virtual void HandleTranslationUnit(clang::ASTContext &Context) {
    Visitor.TraverseDecl(Context.getTranslationUnitDecl());
    Visitor.toString(outfile);
  }
private:
  CythonVisitor Visitor;
  const char *const outfile;
};

class TranspilationAction : public clang::ASTFrontendAction {
public:
  TranspilationAction(const char *const header_file, const char *const outfile) : header_file(header_file), outfile(outfile) {}
  virtual std::unique_ptr<clang::ASTConsumer> CreateASTConsumer(
        clang::CompilerInstance &Compiler, llvm::StringRef InFile) {
    return std::unique_ptr<clang::ASTConsumer>(
        new TranspilationConsumer(&Compiler.getASTContext(), header_file, outfile));
  }
private:
  const char *const header_file;
  const char *const outfile;
};

extern "C" {
  void transpile(const char *const code, const char *const header_file, const char *const outfile) {
    clang::tooling::runToolOnCode(std::make_unique<TranspilationAction>(header_file, outfile), code);
  }
}