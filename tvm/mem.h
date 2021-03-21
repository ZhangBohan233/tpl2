//
// Created by zbh on 2020/9/15.
//

#ifndef TPL2_MEM_H
#define TPL2_MEM_H

#include "util.h"

#define MEM_BLOCK (VM_BITS / 2)

typedef struct LinkedNode {
    tp_int addr;
    struct LinkedNode *next;
} LinkedNode;

LinkedNode *ava_pool;
LinkedNode *available;
//LinkedNode *fragment_pool;
//LinkedNode *fragments;

LinkedNode *build_link(tp_int lower, tp_int upper, LinkedNode **pool);

tp_int malloc_link(tp_int block_count);

void print_link(LinkedNode *head);

LinkedNode *sort_link(LinkedNode *head);

int link_len(LinkedNode *head);

void free_link_pool(LinkedNode *pool);

#endif //TPL2_MEM_H
