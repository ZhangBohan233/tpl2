//
// Created by zbh on 2021/4/5.
//

#ifndef TPL2_GC_H
#define TPL2_GC_H

#include "util.h"
#include "tvm.h"

#define HASH_TABLE_SIZE (MEMORY_SIZE / 128)

#define MEM_ALIGN(NUM) (((NUM) & ANDER) == 0 ? (NUM) : (((NUM) >> SHIFT) + 1) << SHIFT)

tp_int heap_counter;

typedef struct HashLink {
    tp_int value;
    tp_int parent;
    struct HashLink *next;
} HashLink;

typedef struct HashEntry {
    tp_int key;
    tp_int key1;
    tp_int key2;
    struct HashLink *value;
    struct HashEntry *next;
} HashEntry;

typedef struct HashTable {
    size_t capacity;
    size_t size;
    HashEntry **array;
} HashTable;

typedef struct MapEntry {
    tp_int key;
    tp_int value;
    struct MapEntry *next;
} MapEntry;

typedef struct HashMap {
    size_t capacity;
    MapEntry **array;
} HashMap;

void create_heap(tp_int heap_begins);

void free_heap();

tp_int heap_allocate(tp_int length, int print_gc_info);

void gc(int print_gc_info);

#endif //TPL2_GC_H
