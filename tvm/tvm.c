//
// Created by zbh on 2020/8/25.
//

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <locale.h>
#include "os_spec.h"
#include "mem.h"
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

#define MEMORY_SIZE 16384
#define RECURSION_LIMIT 1000

tp_int stack_end;
tp_int literal_end;
tp_int global_end;
tp_int functions_end;
tp_int entry_end;
tp_int class_header_end;

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

int argc;
char **argv;

tp_int tvm_set_args();

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
    class_header_end = literal_end + bytes_to_int(src_code + 16 + INT_LEN * 3);

    tp_int copy_len = code_length - 16 - INT_LEN * 5;  // stack, global, literal, class_headers, entry
    entry_end = global_end + copy_len;

    if (global_end + copy_len > MEMORY_SIZE) {
        fprintf(stderr, "Not enough memory to start vm. \n");
        ERROR_CODE = ERR_MEMORY_OUT;
        return 1;
    }

    memcpy(MEMORY + global_end, src_code + 16 + INT_LEN * 4, copy_len);

    functions_end = entry_end - entry_len;
    pc = functions_end;

    available = build_ava_link(entry_end, MEMORY_SIZE);

    return 0;
}

void nat_return_int(tp_int value) {
    int_to_bytes(MEMORY + ret_stack[ret_p--], value);
}

void nat_return() {
    ret_p--;
}

tp_int get_nat_return_addr() {
    return ret_stack[ret_p];
}

/*
 * Rule of nat_ function:
 *
 * 1. First code line must be push_fp
 * 2. Second code line must be push(stack length of this function)
 * 3. Last code line must be pull_fp
 * 4. If this function has a declared non-void return type, call some 'nat_return' function before pull_fp
 */

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

    tp_float arg = bytes_to_float(MEMORY + true_addr(0));
    tp_printf("%f\n", arg);

    pull_fp
}

void nat_print_str() {
    push_fp
    push(PTR_LEN)

    tp_int arr_ptr = bytes_to_int(MEMORY + true_addr(0));
    tp_int arr_len = bytes_to_int(MEMORY + true_addr(arr_ptr));
    for (int i = 0; i < arr_len; i++) {
        tp_char arg = bytes_to_char(MEMORY + true_addr(arr_ptr + INT_LEN + i * CHAR_LEN));
        wprintf(L"%c", arg);
    }

    pull_fp
}

void nat_println_str() {
    push_fp
    push(FLOAT_LEN)

    tp_int arr_ptr = bytes_to_int(MEMORY + true_addr(0));
    tp_int arr_len = bytes_to_int(MEMORY + true_addr(arr_ptr));
    for (int i = 0; i < arr_len; i++) {
        tp_char arg = bytes_to_char(MEMORY + true_addr(arr_ptr + INT_LEN + i * CHAR_LEN));
        wprintf(L"%c", arg);
    }
    printf("\n");

    pull_fp
}

void nat_clock() {
    push_fp

    tp_int t = get_time();
    nat_return_int(t);

    pull_fp
}

tp_int _malloc_essential(tp_int asked_len) {
    tp_int real_len = asked_len + INT_LEN;
    tp_int allocate_len =
            real_len % MEM_BLOCK == 0 ? real_len / MEM_BLOCK : real_len / MEM_BLOCK + 1;
    tp_int location = malloc_link(allocate_len);

    if (location <= 0) {
        int ava_size = link_len(available) * MEM_BLOCK - INT_LEN;
        fprintf(stderr, "Cannot allocate length %lld, available memory %d\n", asked_len, ava_size);
        ERROR_CODE = ERR_MEMORY_OUT;
        return 0;
    }

    int_to_bytes(MEMORY + location, allocate_len);  // stores the allocated length
    return location + INT_LEN;
}

void nat_malloc() {
    push_fp
    push(INT_LEN)

    tp_int asked_len = bytes_to_int(MEMORY + true_addr(0));
    tp_int malloc_res = _malloc_essential(asked_len);

    nat_return_int(malloc_res);

    pull_fp
}

void _free_link(int_fast64_t real_ptr, int_fast64_t alloc_len) {
    LinkedNode *head = available;
    LinkedNode *after = available;
    while (after->addr < real_ptr) {
        head = after;
        after = after->next;
    }
//    printf("%lld, %lld\n", head->addr, after->addr);
    int_fast64_t index_in_pool = (real_ptr - entry_end) / MEM_BLOCK + 1;
//    printf("%lld\n", index_in_pool);
    for (int_fast64_t i = 0; i < alloc_len; ++i) {
        LinkedNode *node = &ava_pool[index_in_pool++];
        node->addr = real_ptr + i * MEM_BLOCK;
        head->next = node;
        head = node;
    }
    if (head->addr >= after->addr) {
        fprintf(stderr, "Heap memory collision");
        ERROR_CODE = ERR_HEAP_COLLISION;
        head->next = NULL;  // avoid cyclic reference
        return;
    }
    head->next = after;
}

void nat_free() {
    push_fp
    push(PTR_LEN)

    tp_int free_ptr = bytes_to_int(MEMORY + true_addr(0));
    int_fast64_t real_addr = free_ptr - INT_LEN;
    int_fast64_t alloc_len = bytes_to_int(MEMORY + real_addr);

    if (real_addr < entry_end || real_addr > MEMORY_SIZE) {
        printf("Cannot free pointer: %lld outside heap\n", real_addr);
        ERROR_CODE = ERR_HEAP_COLLISION;
        return;
    }
    _free_link(real_addr, alloc_len);

    pull_fp
}

tp_int _array_total_len(tp_int atom_len, const tp_int *dimensions, int dim_arr_len, int index_in_dim) {
    tp_int dim = dimensions[index_in_dim];
    if (dim == -1) return PTR_LEN;

    if (index_in_dim == dim_arr_len - 1) return dimensions[index_in_dim] * atom_len + INT_LEN;
    else {
        tp_int res = dim * PTR_LEN + INT_LEN;
        for (int i = 0; i < dim; i++) {
            res += _array_total_len(atom_len, dimensions, dim_arr_len, index_in_dim + 1);
        }
        return res;
    }
}

void _create_arr_rec(tp_int to_write, tp_int atom_len,
                     const tp_int *dimensions, int dim_arr_len, int index_in_dim, tp_int *cur_heap) {
    tp_int dim = dimensions[index_in_dim];
//    printf("%lld\n", dim);
    if (dim == -1) {
        *cur_heap += PTR_LEN;
        return;
    }

    int_to_bytes(MEMORY + to_write, *cur_heap);

    tp_int ele_len;
    if (index_in_dim == dim_arr_len - 1) ele_len = atom_len;
    else ele_len = PTR_LEN;

    tp_int cur_arr_addr = *cur_heap;
    *cur_heap += (dim * ele_len) + INT_LEN;

    int_to_bytes(MEMORY + cur_arr_addr, dim);  // write array size

    tp_int first_ele_addr = cur_arr_addr + INT_LEN;

    if (index_in_dim < dim_arr_len - 1) {
        for (int i = 0; i < dim; i++) {
            _create_arr_rec(first_ele_addr + i * PTR_LEN,
                            atom_len,
                            dimensions,
                            dim_arr_len,
                            index_in_dim + 1,
                            cur_heap);
        }
    }

}

tp_float float_mod(tp_float d1, tp_float d2) {
    while (d1 >= d2) {
        d1 -= d2;
    }
    return d1;
}

void nat_heap_array() {
    push_fp
    push(INT_LEN * 2)

    tp_int atom_size = bytes_to_int(MEMORY + true_addr(0));
    tp_int dim_arr_addr = bytes_to_int(MEMORY + true_addr(INT_LEN));

    tp_int dim_arr_len = bytes_to_int(MEMORY + dim_arr_addr);
    tp_int *dimension = malloc(sizeof(tp_int) * dim_arr_len);

    for (int i = 0; i < dim_arr_len; i++) {
        dimension[i] = bytes_to_int(MEMORY + dim_arr_addr + (i + 1) * INT_LEN);
//        printf("%lld, ", dimension[i]);
    }
    if (dimension[0] < 0) {
        fprintf(stderr, "Cannot create heap array of unspecified size. ");
        ERROR_CODE = ERR_NATIVE_INVOKE;
        return;
    }
//    print_array(dimension, dim_arr_len);

    tp_int total_heap_len = _array_total_len(atom_size, dimension, dim_arr_len, 0);
//    printf("%lld %lld %lld\n", atom_size, dim_arr_addr, total_heap_len);

    tp_int heap_loc = _malloc_essential(total_heap_len);
//    printf("%lld\n", heap_loc);

    tp_int cur_heap_loc = heap_loc;
    _create_arr_rec(get_nat_return_addr(), atom_size, dimension, dim_arr_len, 0, &cur_heap_loc);

    free(dimension);
    nat_return();

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
        case 8:  // print_str
            nat_print_str();
            break;
        case 9:  // println_str
            nat_println_str();
            break;
        case 10:  // malloc
            nat_malloc();
            break;
        case 11:  // free
            nat_free();
            break;
        case 12:  // heap_array
            nat_heap_array();
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
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                int_to_bytes(MEMORY + true_addr(regs[reg1].int_value), true_addr(regs[reg2].int_value));
//                memcpy(MEMORY + true_addr(regs[reg1].int_value), regs[reg2].bytes, INT_LEN);
                break;
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
            case 26:  // rloadc_abs
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                memcpy(regs[reg1].bytes, MEMORY + regs[reg2].int_value, CHAR_LEN);
                break;
            case 27:  // rloadb_abs
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].byte_value = MEMORY[regs[reg2].int_value];
//                memcpy(regs[reg1].bytes, MEMORY + regs[reg2].byte_value, 1);
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
            case 50:  // addf
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].double_value = regs[reg1].double_value + regs[reg2].double_value;
                break;
            case 51:  // subf
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].double_value = regs[reg1].double_value - regs[reg2].double_value;
                break;
            case 52:  // mulf
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].double_value = regs[reg1].double_value * regs[reg2].double_value;
                break;
            case 53:  // divf
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].double_value = regs[reg1].double_value / regs[reg2].double_value;
                break;
            case 54:  // modf
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].double_value = float_mod(regs[reg1].double_value, regs[reg2].double_value);
                break;
            case 55:  // eqf
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].double_value == regs[reg2].double_value;
                break;
            case 56:  // nef
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].double_value != regs[reg2].double_value;
                break;
            case 57:  // gtf
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].double_value > regs[reg2].double_value;
                break;
            case 58:  // ltf
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].double_value < regs[reg2].double_value;
                break;
            case 59:  // gef
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].double_value >= regs[reg2].double_value;
                break;
            case 60:  // lef
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].double_value <= regs[reg2].double_value;
                break;
            case 61:  // negf
                reg1 = MEMORY[pc++];
                regs[reg1].double_value = -regs[reg1].double_value;
                break;
            case 65:  // i_to_f
                reg1 = MEMORY[pc++];
                regs[reg1].double_value = regs[reg1].int_value;
                break;
            case 66:  // f_to_i
                reg1 = MEMORY[pc++];
                regs[reg1].int_value = regs[reg1].double_value;
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
            case 72:  // storec_abs
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                char_to_bytes(MEMORY + regs[reg1].int_value, regs[reg2].char_value);
//                memcpy(MEMORY + regs[reg1].char_value, regs[reg2].bytes, CHAR_LEN);
                break;
            case 79:  // main args
                int_to_bytes(MEMORY + true_addr_sp(0), tvm_set_args());
                break;
            case 80:  // loadb
                reg1 = MEMORY[pc++];
                memcpy(regs[reg1].bytes, MEMORY + pc, INT_LEN);
                pc += INT_LEN;
//                regs[reg1].char_value = bytes_to_char(MEMORY + true_addr(regs[reg1].int_value));
                regs[reg1].byte_value = MEMORY[true_addr(regs[reg1].int_value)];
                break;
            case 81:  // storeb
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                MEMORY[true_addr(regs[reg1].int_value)] = regs[reg2].byte_value;
//                char_to_bytes(MEMORY + true_addr(regs[reg1].int_value), regs[reg2].char_value);
                break;
            case 82:  // storeb_abs
                reg1 = MEMORY[pc++];
                reg2 = MEMORY[pc++];
                MEMORY[regs[reg1].int_value] = regs[reg2].byte_value;
//                char_to_bytes(MEMORY + regs[reg1].int_value, regs[reg2].char_value);
//                memcpy(MEMORY + regs[reg1].char_value, regs[reg2].bytes, CHAR_LEN);
                break;
            default:
                ERROR_CODE = ERR_INSTRUCTION;
                break;
        }
    }
}

void tvm_shutdown() {
    free_link_pool(ava_pool);
}

tp_int tvm_set_args() {
    tp_int total_malloc_len = INT_LEN;
    tp_int *lengths = malloc(sizeof(tp_int) * argc);
    for (int i = 0; i < argc; i++) {
        tp_int len = (tp_int) strlen(argv[i]);
        lengths[i] = len;
        total_malloc_len += INT_LEN + len * CHAR_LEN;
    }

    tp_int arr_ptr = _malloc_essential(total_malloc_len);
    int_to_bytes(MEMORY + arr_ptr, (tp_int) argc);

    tp_int cur_ptr = arr_ptr + INT_LEN + argc * PTR_LEN;
    for (int i = 0; i < argc; i++) {
        char *str = argv[i];
        tp_int len = lengths[i];
        tp_int str_ptr = cur_ptr;
        cur_ptr += INT_LEN + len * CHAR_LEN;
        int_to_bytes(MEMORY + str_ptr, len);  // write string length
        for (int j = 0; j < len; j++) {
            char_to_bytes(MEMORY + str_ptr + INT_LEN + j * CHAR_LEN, str[j]);  // write char to string
        }
        int_to_bytes(MEMORY + arr_ptr + INT_LEN + i * INT_LEN, str_ptr);  // write string ptr to string[]
    }

    free(lengths);

    return arr_ptr;
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
        if (i % INT_LEN == 0) printf("| ");
        printf("%d ", MEMORY[i]);
    }

    tp_printf("\nLiteral %d: ", global_end)
    for (; i < literal_end; ++i) {
        printf("%d ", MEMORY[i]);
    }

    tp_printf("\nClass header %d: ", literal_end);
    for (; i < class_header_end; ++i) {
        printf("%d ", MEMORY[i]);
    }

    tp_printf("\nFunctions %d: ", class_header_end)
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

    argc = vm_argc;
    argv = vm_argv;

    unsigned char *codes = read_file(file_name, &read);
    if (codes == NULL) {
        fprintf(stderr, "Cannot read file. ");
        return;
    }

    if (tvm_load(codes, read)) exit(ERR_VM_OPT);
//    tvm_set_args(vm_argc, vm_argv);

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
