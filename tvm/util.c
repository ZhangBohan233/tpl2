//
// Created by zbh on 2020/8/25.
//

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "util.h"

unsigned char *read_file(char *file_name, int *length_ptr) {
    FILE *fp = malloc(sizeof(FILE));
    int res = fopen_s(&fp, file_name, "rb");
    if (res != 0) {
        fprintf(stderr, "Open error");
        free(fp);
        return NULL;
    }
    fseek(fp, 0, SEEK_END);
    int len = ftell(fp);
    *length_ptr = len;
    unsigned char *array = malloc(sizeof(unsigned char) * len);
    fseek(fp, 0, SEEK_SET);
    unsigned int read = fread(array, sizeof(unsigned char), len, fp);
    if (read != len) {
        fclose(fp);
        fprintf(stderr, "Read error. Expected length %d, actual bytes %d\n", len, read);
        return NULL;
    }
    fclose(fp);
    return array;
}

tp_int bytes_to_int64(const unsigned char *b) {
    union {
        tp_int value;
        unsigned char arr[8];
    } i64;
    memcpy(i64.arr, b, 8);
    return i64.value;
}

void int_to_bytes64(unsigned char *b, tp_int i) {
    union {
        tp_int value;
        unsigned char arr[8];
    } i64;
    i64.value = i;
    memcpy(b, i64.arr, 8);
}

tp_int bytes_to_int32(const unsigned char *b) {
    union {
        tp_int value;
        unsigned char arr[4];
    } i32;
    memcpy(i32.arr, b, 4);
    return i32.value;
}

void int_to_bytes32(unsigned char *b, tp_int i) {
    union {
        tp_int value;
        unsigned char arr[4];
    } i32;
    i32.value = i;
    memcpy(b, i32.arr, 4);
}

tp_float bytes_to_float64(const unsigned char *bytes) {
    union {
        tp_float d;
        unsigned char b[8];
    } dou;
    memcpy(dou.b, bytes, 8);
    return dou.d;
}

void float_to_bytes64(unsigned char *bytes, tp_float d) {
    union {
        tp_float d;
        unsigned char b[8];
    } dou;
    dou.d = d;
    memcpy(bytes, dou.b, 8);
}

tp_float bytes_to_float32(const unsigned char *bytes) {
    union {
        tp_float d;
        unsigned char b[4];
    } dou;
    memcpy(dou.b, bytes, 4);
    return dou.d;
}

void float_to_bytes32(unsigned char *bytes, tp_float d) {
    union {
        tp_float d;
        unsigned char b[4];
    } dou;
    dou.d = d;
    memcpy(bytes, dou.b, 4);
}

char *format_bits(const char *format) {
    int len = 0;
    int d_count = 0;
    char c;
    int mark = 0;
    while ((c = format[len]) != '\0') {
        if (mark && c == 'd') {
            d_count++;
            mark = 0;
        }
        if (c == '%') mark = 1;
        len++;
    }
    char *dst;
    if (VM_BITS == 32) {
        dst = malloc(len + 1);
        memcpy(dst, format, len);
        dst[len] = '\0';
    } else {
        dst = malloc(len + 1 + d_count * 2);
        mark = 0;
        int dst_i = 0;
        for (int i = 0; i < len; i++) {
            c = format[i];
            if (mark && c == 'd') {
                dst[dst_i++] = 'l';
                dst[dst_i++] = 'l';
                mark = 0;
            }
            if (c == '%') mark = 1;
            dst[dst_i++] = c;
        }
        dst[len + d_count * 2] = '\0';
    }
    return dst;
}

//void tp_printf(const char *format, ...) {
//    printf(format, __VA_ARGS__);
//}
