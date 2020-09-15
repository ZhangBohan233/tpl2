//
// Created by zbh on 2020/9/15.
//

#ifndef TPL2_MEM_H
#define TPL2_MEM_H

#include "util.h"

#define MEM_BLOCK 16

typedef struct LinkedNode {
    tp_int addr;
    struct LinkedNode *next;
} LinkedNode;

LinkedNode *ava_pool;
LinkedNode *available;

LinkedNode *build_ava_link(tp_int lower, tp_int upper);

tp_int malloc_link(tp_int block_count);

void print_link(LinkedNode *head);

LinkedNode *sort_link(LinkedNode *head);

int link_len(LinkedNode *head);

void free_link_pool(LinkedNode *pool);

#endif //TPL2_MEM_H
