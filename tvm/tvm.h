//
// Created by zbh on 2020/8/25.
//

#ifndef TPL2_TVM_H
#define TPL2_TVM_H

#include "util.h"
#include "positions.h"

#define ERR_NATIVE_INVOKE 2
#define ERR_VM_OPT 3
#define ERR_HEAP_COLLISION 4
#define ERR_INSTRUCTION 5
#define ERR_MEMORY_OUT 6
#define ERR_STACK_OVERFLOW 7
#define ERR_SEGMENT 8
#define ERR_NULL_POINTER 9

#define RECURSION_LIMIT 1000
#define CLASS_FIXED_HEADER (INT_PTR_LEN * 2)

tp_int stack_end;
tp_int literal_end;
tp_int global_end;
tp_int class_literal_end;
tp_int class_header_end;
tp_int functions_end;
tp_int entry_end;
tp_int heap_start;  // there might be small gaps between entry_end and heap_start, due to alignment

unsigned char MEMORY[MEMORY_SIZE];

tp_int call_stack[RECURSION_LIMIT];  // stores fp (frame pointer)
int call_p;

tp_int pc_stack[RECURSION_LIMIT];  // stores pc (program counter)
int pc_p;

tp_int ret_stack[RECURSION_LIMIT];  // stores true addr of return addresses
int ret_p;

tp_int runtime_type_abs(tp_int abs_addr, tp_int segment_begin);

tp_int runtime_type(tp_int rel_addr);

tp_int field_type(tp_int class_ptr, tp_int field_pos);

void tvm_run(int p_memory, int p_exit, int p_gc, char *file_name, int vm_argc, char **vm_argv);

#endif //TPL2_TVM_H
