//
// Created by zbh on 2020/8/25.
//

#ifndef TPL2_UTIL_H
#define TPL2_UTIL_H

#include <stdint.h>

#define INT_LEN 8
#define FLOAT_LEN 8

typedef int_fast64_t tp_int;
typedef double tp_float;

unsigned char *read_file(char *file_name, int *length_ptr);

tp_int bytes_to_int(const unsigned char *bytes);

void int_to_bytes(unsigned char *b, tp_int i);

tp_float bytes_to_double(const unsigned char *bytes);

void double_to_bytes(unsigned char *b, tp_float d);

#endif //TPL2_UTIL_H
