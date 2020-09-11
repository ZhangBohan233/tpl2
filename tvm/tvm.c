//
// Created by zbh on 2020/8/25.
//

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <locale.h>
#include "os_spec.h"
#include "tvm.h"

// The error code, set by virtual machine. Used to tell the main loop that the process is interrupted
// Interrupt the vm if the code is not 0
//
// 0: No error
// 1: Memory address error
// 2: Native invoke error
// 3: VM option error

const unsigned char SIGNATURE[] = "TPC_";

int ERROR_CODE = 0;
char *ERR_MSG = "";

#define true_addr(ptr) (ptr < stack_end && call_p >= 0 ? ptr + fp : ptr)
#define true_addr_sp(ptr) (ptr < stack_end ? ptr + sp : ptr)

#define push(n) sp += n; if (sp >= stack_end) ERROR_CODE = ERR_STACK_OVERFLOW;
#define push_fp call_stack[++call_p] = fp; fp = sp;
#define pull_fp sp = fp; fp = call_stack[call_p--];

#define MEMORY_SIZE 8192
#define RECURSION_LIMIT 1000

tp_int stack_end;
tp_int literal_end;
tp_int global_end;
tp_int functions_end;
tp_int entry_end;

unsigned char MEMORY[MEMORY_SIZE];

tp_int sp = 1 + INT_LEN;
tp_int fp = 1;
tp_int pc = 0;

tp_int call_stack[RECURSION_LIMIT];  // stores fp (frame pointer)
int call_p = -1;

tp_int pc_stack[RECURSION_LIMIT];
int pc_p = -1;

tp_int ret_stack[RECURSION_LIMIT];  // stores true addr of return addresses
int ret_p = -1;

int vm_check(const unsigned char *src_code) {
    for (int i = 0; i < 4; i++) {
        if (src_code[i] != SIGNATURE[i]) {
            fprintf(stderr, "This is not a compiled trash program. ");
            return 1;
        }
    }
    if (src_code[4] != VM_BITS) {
        fprintf(stderr, "%d bits code cannot run on %d bits virtual machine. ", src_code[4], VM_BITS);
        return 1;
    }

    return 0;
}

int tvm_load(const unsigned char *src_code, const int code_length) {
    int check = vm_check(src_code);
    if (check != 0) return check;

    tp_int entry_len = bytes_to_int(src_code + code_length - INT_LEN);

    stack_end = bytes_to_int(src_code + 16);  // 16 is fixed header length
    global_end = stack_end + bytes_to_int(src_code + 16 + INT_LEN);
    literal_end = global_end + bytes_to_int(src_code + 16 + INT_LEN * 2);

    tp_int copy_len = code_length - 16 - INT_LEN * 4;  // stack, global, literal, entry
    entry_end = global_end + copy_len;

    memcpy(MEMORY + global_end, src_code + 16 + INT_LEN * 3, copy_len);

    functions_end = entry_end - entry_len;
    pc = functions_end;

    return 0;
}

void nat_return_int(tp_int value) {
    int_to_bytes(MEMORY + ret_stack[ret_p--], value);
}

void nat_print_int() {
    push_fp
    push(INT_LEN)

    tp_int arg = bytes_to_int(MEMORY + true_addr(0));
    tp_printf("%d", arg);

    pull_fp
}

void nat_println_int() {
    push_fp
    push(INT_LEN)

    tp_int arg = bytes_to_int(MEMORY + true_addr(0));
    tp_printf("%d\n", arg);

    pull_fp
}

void nat_print_char() {
    push_fp
    push(CHAR_LEN)

    tp_char arg = bytes_to_char(MEMORY + true_addr(0));
    wprintf(L"%c", arg);

    pull_fp
}

void nat_println_char() {
    push_fp
    push(CHAR_LEN)

    tp_char arg = bytes_to_char(MEMORY + true_addr(0));
    wprintf(L"%c\n", arg);

    pull_fp
}

void nat_print_float() {
    push_fp
    push(FLOAT_LEN)

    tp_float arg = bytes_to_float(MEMORY + true_addr(0));
    tp_printf("%f", arg);

    pull_fp
}

void nat_println_float() {
    push_fp
    push(FLOAT_LEN)

    tp_float arg = bytes_to_float32(MEMORY + true_addr(0));
    tp_printf("%f\n", arg);

    pull_fp
}

void nat_clock() {
    push_fp

    tp_int t = get_time();
    nat_return_int(t);

    pull_fp
}

void invoke(tp_int func_ptr) {
    tp_int func_id = bytes_to_int(MEMORY + func_ptr);
    switch (func_id) {
        case 1:  // print_int
            nat_print_int();
            break;
        case 2:  // println_int
            nat_println_int();
            break;
        case 3:  // clock
            nat_clock();
            break;
        case 4:  // print_char
            nat_print_char();
            break;
        case 5:  // println_char
            nat_println_char();
            break;
        case 6:  // print_float
            nat_print_float();
            break;
        case 7:  // println_float
            nat_println_float();
            break;
        default:
            ERROR_CODE = ERR_NATIVE_INVOKE;
            ERR_MSG = "No such native invoke. ";
            break;
    }
}

void tvm_mainloop() {
    union reg64 {
        tp_int int_value;
        tp_float double_value;
        tp_char char_value;
        tp_byte byte_value;
        unsigned char bytes[INT_LEN];
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
                pc += bytes_to_int(MEMORY + pc) + INT_LEN;
                break;
            case 11:  // move
                break;
            case 12:  // push
            push(bytes_to_int(MEMORY + pc))
                pc += INT_LEN;
                break;
            case 13:  // ret
                pc = pc_stack[pc_p--];
                break;
            case 14:  // push fp
            push_fp
                break;
            case 15:  // pull fp
            pull_fp
                break;
            case 16:  // set ret
                reg1 = MEMORY[pc++];
                ret_stack[++ret_p] = true_addr(regs[reg1].int_value);
//                printf("ret %lld\n", ret_stack[ret_p]);
                break;
            case 17:  // call fn
//                printf("call\n");
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
            case 23:  // if_zero_jump
                reg1 = MEMORY[pc++];
//                printf("jump %lld\n", bytes_to_int(MEMORY + pc));
                if (regs[reg1].int_value == 0) {
                    pc += bytes_to_int(MEMORY + pc) + INT_LEN;
                } else {
                    pc += INT_LEN;
                }
                break;
            case 24:  // invoke
                invoke(true_addr(bytes_to_int(MEMORY + pc)));
                pc += INT_LEN;
                break;
            case 25:  // rload_abs
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                memcpy(regs[reg1].bytes, MEMORY + regs[reg2].int_value, INT_LEN);
                break;
            case 30:  // addi
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].int_value + regs[reg2].int_value;
                break;
            case 31:  // subi
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].int_value - regs[reg2].int_value;
                break;
            case 32:  // muli
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].int_value * regs[reg2].int_value;
                break;
            case 33:  // divi
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].int_value / regs[reg2].int_value;
                break;
            case 34:  // modi
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].int_value % regs[reg2].int_value;
                break;
            case 35:  // eqi
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].int_value == regs[reg2].int_value;
                break;
            case 36:  // nei
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].int_value != regs[reg2].int_value;
                break;
            case 37:  // gti
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].int_value > regs[reg2].int_value;
                break;
            case 38:  // lti
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].int_value < regs[reg2].int_value;
                break;
            case 39:  // gei
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].int_value >= regs[reg2].int_value;
                break;
            case 40:  // lei
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].int_value <= regs[reg2].int_value;
                break;
            case 41:  // negi
                reg1 = MEMORY[pc++];
                regs[reg1].int_value = -regs[reg1].int_value;
                break;
            case 42:  // not
                reg1 = MEMORY[pc++];
                regs[reg1].int_value = !regs[reg1].int_value;
                break;
            case 70:  // loadc
                reg1 = MEMORY[pc++];
                memcpy(regs[reg1].bytes, MEMORY + pc, INT_LEN);
                pc += INT_LEN;
                regs[reg1].char_value = bytes_to_char(MEMORY + true_addr(regs[reg1].int_value));
                break;
            case 71:  // storec
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                char_to_bytes(MEMORY + true_addr(regs[reg1].int_value), regs[reg2].char_value);
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
        if (i % INT_LEN == 0) printf("| ");
    }

    tp_printf("\nGlobal %d: ", stack_end)
    for (; i < global_end; ++i) {
        printf("%d ", MEMORY[i]);
    }

    tp_printf("\nLiteral %d: ", global_end)
    for (; i < literal_end; ++i) {
        printf("%d ", MEMORY[i]);
    }

    tp_printf("\nFunctions %d: ", literal_end)
    for (; i < functions_end; i++) {
        printf("%d ", MEMORY[i]);
    }

    tp_printf("\nEntry %d: ", functions_end);
    for (; i < entry_end; i++) {
        printf("%d ", MEMORY[i]);
    }

    tp_printf("\nHeap %d: ", entry_end)
    for (; i < entry_end + 128; i++) {
        printf("%d ", MEMORY[i]);
        if ((i - entry_end) % INT_LEN == 7) printf("| ");
    }
    printf("\n");
}

void print_error(int error_code) {
    switch (error_code) {
        case ERR_STACK_OVERFLOW:
            fprintf(stderr, "\nStack overflow: ");
            break;
        case ERR_NATIVE_INVOKE:
            fprintf(stderr, "\nNative invoke error: ");
            break;
        case ERR_HEAP_COLLISION:
            fprintf(stderr, "\nHeap collision: ");
            break;
        case ERR_INSTRUCTION:
            fprintf(stderr, "\nUnexpected instruction: ");
            break;
        default:
            fprintf(stderr, "\nSomething wrong: ");
            break;
    }
    fprintf(stderr, "%s\n", ERR_MSG);
}

void tvm_run(int p_memory, int p_exit, char *file_name, int vm_argc, char **vm_argv) {
    int read;

    setlocale(LC_ALL, "chs");

    unsigned char *codes = read_file(file_name, &read);
    if (codes == NULL) {
        fprintf(stderr, "Cannot read file. ");
        return;
    }

    if (tvm_load(codes, read)) exit(ERR_VM_OPT);
    tvm_set_args(vm_argc, vm_argv);

    tvm_mainloop();

    tp_int main_rtn_ptr = 1;

    if (ERROR_CODE != 0) {
        int_to_bytes(MEMORY + main_rtn_ptr, ERROR_CODE);
        print_error(ERROR_CODE);
    }

    if (p_memory) print_memory();
    if (p_exit) tp_printf("Trash program finished with exit code %d\n", bytes_to_int(MEMORY + main_rtn_ptr))

    tvm_shutdown();
}
