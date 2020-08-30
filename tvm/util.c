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
        perror("Open error");
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
        printf("Read error. Expected length %d, actual bytes %d\n", len, read);
        return NULL;
    }
    fclose(fp);
    return array;
}

/*
 * This function is only valid when INT_LEN == 8
 */
tp_int bytes_to_int(const unsigned char *b) {
    union {
        tp_int value;
        unsigned char arr[8];
    } i64;
    memcpy(i64.arr, b, 8);
    return i64.value;
}

void int_to_bytes(unsigned char *b, tp_int i) {
    union {
        tp_int value;
        unsigned char arr[8];
    } i64;
    i64.value = i;
    memcpy(b, i64.arr, 8);
}

tp_float bytes_to_double(const unsigned char *bytes) {
    union {
        tp_float d;
        unsigned char b[8];
    } dou;
    memcpy(dou.b, bytes, 8);
    return dou.d;
}

void double_to_bytes(unsigned char *bytes, tp_float d) {
    union {
        tp_float d;
        unsigned char b[8];
    } dou;
    dou.d = d;
    memcpy(bytes, dou.b, 8);
}
