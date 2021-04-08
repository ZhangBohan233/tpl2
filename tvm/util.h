//
// Created by zbh on 2020/8/25.
//

#ifndef TPL2_UTIL_H
#define TPL2_UTIL_H

#include <stdint.h>
#include <stdlib.h>

//
// To modify VM bits, modify all of the following
//

#define BYTECODE_VERSION 1
#define VM_BITS 32

#if VM_BITS == 32
    #define INT_PTR_LEN 4
    #define FLOAT_LEN 4
    #define SHIFT 2
    #define ANDER 0b11

    #define bytes_to_int(b) bytes_to_int32(b)
    #define int_to_bytes(b, i) int_to_bytes32(b, i)
    #define bytes_to_float(b) bytes_to_float32(b)
    #define float_to_bytes(b, i) float_to_bytes32(b, i)

    typedef int_fast32_t tp_int;
    typedef float tp_float;
#else
    #define INT_PTR_LEN 8
    #define FLOAT_LEN 8
    #define SHIFT 3
    #define ANDER 0b111

    #define bytes_to_int(b) bytes_to_int64(b)
    #define int_to_bytes(b, i) int_to_bytes64(b, i)
    #define bytes_to_float(b) bytes_to_float64(b)
    #define float_to_bytes(b, i) float_to_bytes64(b, i)

    typedef int_fast64_t tp_int;
    typedef double tp_float;
#endif

#define CHAR_LEN 2
typedef wchar_t tp_char;
typedef unsigned char tp_byte;

//
// end of modification
//

// object header codes

#define INT_CODE 1
#define FLOAT_CODE 2
#define CHAR_CODE 3
#define BYTE_CODE 4
#define OBJECT_CODE 5
#define ARRAY_CODE 6
#define FUNCTION_CODE 7
#define NATIVE_FUNCTION_CODE 8
#define CLASS_CODE 9

#define MEMORY_SIZE 131072

#define tp_printf(fmt, ...) {char *fmt_mod = format_bits(fmt); printf(fmt_mod, __VA_ARGS__); free(fmt_mod);}
#define tp_fprintf(dst, fmt, ...) {char *fmt_mod = format_bits(fmt); fprintf(dst, fmt_mod, __VA_ARGS__); free(fmt_mod);}

tp_int size_of_type(int type_code);

unsigned char *read_file(char *file_name, int *length_ptr);

tp_int bytes_to_int64(const unsigned char *bytes);

void int_to_bytes64(unsigned char *b, tp_int i);

tp_int bytes_to_int32(const unsigned char *bytes);

void int_to_bytes32(unsigned char *b, tp_int i);

tp_char bytes_to_char(const unsigned char *bytes);

void char_to_bytes(unsigned char *b, tp_char i);

tp_float bytes_to_float64(const unsigned char *bytes);

void float_to_bytes64(unsigned char *b, tp_float d);

tp_float bytes_to_float32(const unsigned char *bytes);

void float_to_bytes32(unsigned char *b, tp_float d);

unsigned short bytes_to_ushort(const unsigned char *b);

char *format_bits(const char *format);

void print_array(tp_int *array, int len);

//void tp_printf(const char *format, ...);

#endif //TPL2_UTIL_H
