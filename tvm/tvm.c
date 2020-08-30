//
// Created by zbh on 2020/8/25.
//

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "tvm.h"

// The error code, set by virtual machine. Used to tell the main loop that the process is interrupted
// Interrupt the vm if the code is not 0
//
// 0: No error
// 1: Memory address error
// 2: Native invoke error
// 3: VM option error

const int ERR_STACK_OVERFLOW = 1;
const int ERR_NATIVE_INVOKE = 2;
const int ERR_VM_OPT = 3;
const int ERR_HEAP_COLLISION = 4;
const int ERR_INSTRUCTION = 5;

int ERROR_CODE = 0;

#define true_addr(ptr) (ptr < stack_end && call_p >= 0 ? ptr + fp : ptr)
#define true_addr_sp(ptr) (ptr < stack_end ? ptr + sp : ptr)

#define MEMORY_SIZE 8192
#define RECURSION_LIMIT 1024

tp_int stack_end;
tp_int literal_end;
tp_int global_end;
tp_int functions_end;
tp_int entry_end;

unsigned char MEMORY[MEMORY_SIZE];

tp_int sp = 9;
tp_int fp = 1;
tp_int pc = 0;

tp_int call_stack[RECURSION_LIMIT];  // recursion limit
int call_p = -1;

tp_int pc_stack[RECURSION_LIMIT];
int pc_p = -1;

tp_int ret_stack[RECURSION_LIMIT];  // stores true addr of return addresses
int ret_p = -1;

int tvm_load(const unsigned char *src_code, const int code_length) {
    tp_int entry_len = bytes_to_int(src_code + code_length - INT_LEN);
    stack_end = bytes_to_int(src_code);
    global_end = stack_end + bytes_to_int(src_code + INT_LEN);
    literal_end = global_end + bytes_to_int(src_code + INT_LEN * 2);

    tp_int copy_len = code_length - INT_LEN * 4;
    entry_end = global_end + copy_len;

    memcpy(MEMORY + global_end, src_code + INT_LEN * 3, copy_len);

    functions_end = entry_end - entry_len;
    pc = functions_end;

    return 0;
}

void tvm_mainloop() {
    union reg64 {
        tp_int int_value;
        tp_float double_value;
        unsigned char bytes[8];
    };
    union reg64 regs[8];

    register unsigned char instruction;
    unsigned int reg1, reg2, reg3, reg4;

    while (ERROR_CODE == 0) {
        instruction = MEMORY[pc++];
//        printf("%d\n", instruction);
        switch (instruction) {
            case 0:  // nop
                break;
            case 1:  // sleep
                break;
            case 2:  // load
                reg1 = MEMORY[pc++];
                memcpy(regs[reg1].bytes, MEMORY + pc, INT_LEN);
                pc += INT_LEN;
                memcpy(regs[reg1].bytes, MEMORY + true_addr(regs[reg1].int_value), INT_LEN);
                break;
            case 3:  // iload
                reg1 = MEMORY[pc++];
                regs[reg1].int_value = bytes_to_int(MEMORY + pc);
                pc += INT_LEN;
                break;
            case 4:  // aload
                reg1 = MEMORY[pc++];
                memcpy(regs[reg1].bytes, MEMORY + pc, INT_LEN);
                pc += INT_LEN;
                regs[reg1].int_value = true_addr(regs[reg1].int_value);
                break;
            case 5:  // aload_sp
                reg1 = MEMORY[pc++];
                memcpy(regs[reg1].bytes, MEMORY + pc, INT_LEN);
                pc += INT_LEN;
                regs[reg1].int_value = true_addr_sp(regs[reg1].int_value);
                break;
            case 6:  // store
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                memcpy(MEMORY + true_addr(regs[reg1].int_value), regs[reg2].bytes, INT_LEN);
                break;
            case 7:  // astore
            case 8:  // astore_sp
            case 9:  // store_abs
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                memcpy(MEMORY + regs[reg1].int_value, regs[reg2].bytes, INT_LEN);
                break;
            case 10:  // jump
                break;
            case 11:  // move
                break;
            case 12:  // push
                sp += bytes_to_int(MEMORY + pc);
                pc += INT_LEN;
                break;
            case 13:  // ret
                pc = pc_stack[pc_p--];
                break;
            case 14:  // push fp
                call_stack[++call_p] = fp;
                fp = sp;
                break;
            case 15:  // pull fp
                sp = fp;
                fp = call_stack[call_p--];
                break;
            case 16:  // set ret
                reg1 = MEMORY[pc++];
                ret_stack[++ret_p] = true_addr(regs[reg1].int_value);
//                printf("ret %lld\n", ret_stack[ret_p]);
                break;
            case 17:  // call fn
                pc_stack[++pc_p] = pc + INT_LEN;
                pc = true_addr(bytes_to_int(MEMORY + true_addr(bytes_to_int(MEMORY + pc))));
                break;
            case 18:  // exit
                return;
            case 19:  // true_addr
                reg1 = MEMORY[pc++];
                regs[reg1].int_value = true_addr(regs[reg1].int_value);
                break;
            case 21:  // put_ret
                reg1 = MEMORY[pc++];
                memcpy(MEMORY + ret_stack[ret_p--], regs[reg1].bytes, INT_LEN);
                break;
            case 22:  // copy
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                memcpy(MEMORY + regs[reg1].int_value,
                       MEMORY + regs[reg2].int_value,
                       INT_LEN);
                break;
            case 30:  // addi
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].int_value + regs[reg2].int_value;
                break;
            default:
                ERROR_CODE = ERR_INSTRUCTION;
                break;
        }
    }
}

void tvm_shutdown() {

}

void tvm_set_args(int argc, char **argv) {

}

void print_memory() {
    int i = 0;
    printf("Stack ");
    for (; i < stack_end; i++) {
        printf("%d ", MEMORY[i]);
        if (i % 8 == 0) printf("| ");
    }

    printf("\nGlobal %lld: ", stack_end);
    for (; i < global_end; ++i) {
        printf("%d ", MEMORY[i]);
    }

    printf("\nLiteral %lld: ", global_end);
    for (; i < literal_end; ++i) {
        printf("%d ", MEMORY[i]);
    }

    printf("\nFunctions %lld: ", literal_end);
    for (; i < functions_end; i++) {
        printf("%d ", MEMORY[i]);
    }

    printf("\nEntry %lld: ", functions_end);
    for (; i < entry_end; i++) {
        printf("%d ", MEMORY[i]);
    }

    printf("\nHeap %lld: ", entry_end);
    for (; i < entry_end + 128; i++) {
        printf("%d ", MEMORY[i]);
        if ((i - entry_end) % 8 == 7) printf("| ");
    }
    printf("\n");
}

void tvm_run(int p_memory, int p_exit, char *file_name, int vm_argc, char **vm_argv) {
    int read;

    unsigned char *codes = read_file(file_name, &read);
    if (codes == NULL) {
        fprintf(stderr, "Cannot read file. ");
        return;
    }

    if (tvm_load(codes, read)) exit(ERR_VM_OPT);
    tvm_set_args(vm_argc, vm_argv);

    tvm_mainloop();

    tp_int main_rtn_ptr = 1;

    if (ERROR_CODE != 0) int_to_bytes(MEMORY + main_rtn_ptr, ERROR_CODE);

    if (p_memory) print_memory();
    if (p_exit) printf("Process finished with exit code %lld\n", bytes_to_int(MEMORY + main_rtn_ptr));

    tvm_shutdown();
}
