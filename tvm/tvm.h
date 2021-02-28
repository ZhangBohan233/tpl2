//
// Created by zbh on 2020/8/25.
//

#ifndef TPL2_TVM_H
#define TPL2_TVM_H

#include "util.h"

#define ERR_STACK_OVERFLOW 1
#define ERR_NATIVE_INVOKE 2
#define ERR_VM_OPT 3
#define ERR_HEAP_COLLISION 4
#define ERR_INSTRUCTION 5
#define ERR_MEMORY_OUT 6
#define ERR_SEGMENT 7
#define ERR_NULL_POINTER 8

void tvm_run(int p_memory, int p_exit, char *file_name, int vm_argc, char **vm_argv);

#endif //TPL2_TVM_H
