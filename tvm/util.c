//
// Created by zbh on 2020/8/25.
//

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include "util.h"

tp_int size_of_type(int type_code) {
    switch (type_code) {
        case INT_CODE:
        case OBJECT_CODE:
        case ARRAY_CODE:
        case FUNCTION_CODE:
        case NATIVE_FUNCTION_CODE:
        case CLASS_CODE:
            return INT_PTR_LEN;
        case CHAR_CODE:
            return CHAR_LEN;
        case BYTE_CODE:
            return 1;
        default:
            fprintf(stderr, "Unexpected type code %d.\n", type_code);
            return 0;
    }
}

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

union i64 {
    tp_int value;
    unsigned char arr[8];
};

union i32 {
    tp_int value;
    unsigned char arr[4];
};

union i16 {
    tp_char value;
    unsigned char arr[2];
};

union f64 {
    tp_float d;
    unsigned char b[8];
};

union f32 {
    tp_float d;
    unsigned char b[4];
};

tp_int bytes_to_int64(const unsigned char *b) {
    union i64 un;
    memcpy(un.arr, b, 8);
    return un.value;
}

void int_to_bytes64(unsigned char *b, tp_int i) {
    union i64 un;
    un.value = i;
    memcpy(b, un.arr, 8);
}

tp_int bytes_to_int32(const unsigned char *b) {
    union i32 un;
    memcpy(un.arr, b, 4);
    return un.value;
}

void int_to_bytes32(unsigned char *b, tp_int i) {
    union {
        tp_int value;
        unsigned char arr[4];
    } i32;
    i32.value = i;
    memcpy(b, i32.arr, 4);
}

tp_char bytes_to_char(const unsigned char *b) {
    union i16 un;
    memcpy(un.arr, b, 2);
    return un.value;
}

void char_to_bytes(unsigned char *b, tp_char c) {
    union i16 un;
    un.value = c;
    memcpy(b, un.arr, 2);
}

tp_float bytes_to_float64(const unsigned char *bytes) {
    union f64 un;
    memcpy(un.b, bytes, 8);
    return un.d;
}

void float_to_bytes64(unsigned char *bytes, tp_float d) {
    union f64 un;
    un.d = d;
    memcpy(bytes, un.b, 8);
}

tp_float bytes_to_float32(const unsigned char *bytes) {
    union f32 un;
    memcpy(un.b, bytes, 4);
    return un.d;
}

void float_to_bytes32(unsigned char *bytes, tp_float d) {
    union f32 un;
    un.d = d;
    memcpy(bytes, un.b, 4);
}

unsigned short bytes_to_ushort(const unsigned char *b) {
    union {
        unsigned short value;
        unsigned char arr[2];
    } un;
    memcpy(un.arr, b, 2);
    return un.value;
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

void print_array(tp_int *array, int len) {
    printf("[");
    for (int i = 0 ; i < len; i ++) {
        tp_printf("%d, ", array[i])
    }
    printf("]\n");
}

void test(int arr[][4]) {
    int a[2][3] = {{1, 2, 3}, {4, 5, 6}};
    int b = 2;
}
