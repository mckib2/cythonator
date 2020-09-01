// #include "clang/Tooling/CommonOptionsParser.h"
// #include "clang/Tooling/Refactoring.h"

// using namespace clang::tooling;
// using namespace llvm;

// static llvm::cl::OptionCategory TROpts("Common options for typedef-report");
// const char * addl_help = "Find structs with fields declared via typedef";

// int simple(int argc, const char ** argv) {
//   CommonOptionsParser opt_prs(argc, argv, TROpts, addl_help);
//   RefactoringTool Tool(opt_prs.getCompilations(), opt_prs.getSourcePathList());
//   return 42;
// }
