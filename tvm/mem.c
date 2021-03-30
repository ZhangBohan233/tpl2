//
// Created by zbh on 2020/9/15.
//

#include <stdio.h>
#include "mem.h"

LinkedNode *build_link(tp_int lower, tp_int upper, LinkedNode **pool) {
    tp_int capacity = upper - lower;
    while (capacity % MEM_BLOCK != 0) capacity--;
    tp_int num_nodes = capacity / MEM_BLOCK + 1;
    *pool = malloc(sizeof(LinkedNode) * num_nodes);
    (*pool)->addr = 0;
    LinkedNode *prev = ava_pool;
    for (tp_int i = 1; i < num_nodes; ++i) {
        LinkedNode *node = &(*pool)[i];
        node->addr = lower + (i - 1) * MEM_BLOCK;
        prev->next = node;
        prev = node;
    }
    prev->next = NULL;  // last node
    return *pool;
}

tp_int find_ava(int block_count) {
    LinkedNode *head = available;
    while (head->next != NULL) {
        int i = 0;
        LinkedNode *cur = head->next;
        for (; i < block_count - 1; ++i) {
            LinkedNode *next = cur->next;
            if (next == NULL || next->addr != cur->addr + MEM_BLOCK) {
                break;
            }
            cur = next;
        }
        if (i == block_count - 1) {  // found!
            LinkedNode *node = head->next;
            tp_int found = node->addr;
            head->next = cur->next;
            return found;
        } else {
            head = cur;
        }
    }
    return 0;  // not enough space in heap, ask for re-manage
}

void manage_heap() {
    available = sort_link(available);
}

tp_int malloc_link(tp_int block_count) {
    tp_int location = find_ava(block_count);
    if (location == 0) {
        manage_heap();
        location = find_ava(block_count);
        if (location == 0) return -1;  // cannot find enough space
    }
    return location;
}

void print_link(LinkedNode *head) {
    printf("LinkedList[");
    for (LinkedNode *node = head; node != NULL; node = node->next) {
        tp_printf("%lld, ", node->addr);
    }
    printf("]\n");
}

void split_halves(LinkedNode *node, LinkedNode **back) {
    LinkedNode *fast = node->next;
    LinkedNode *slow = node;
    while (fast != NULL) {
        fast = fast->next;
        if (fast != NULL) {
            slow = slow->next;
            fast = fast->next;
        }
    }
    *back = slow->next;
    slow->next = NULL;
}

LinkedNode *merge_link(LinkedNode *a, LinkedNode *b) {
    if (a == NULL) return b;
    else if (b == NULL) return a;

    LinkedNode *result;
    if (a->addr < b->addr) {
        result = a;
        result->next = merge_link(a->next, b);
    } else {
        result = b;
        result->next = merge_link(a, b->next);
    }
    return result;
}

/**
 * returns the new head.
 */
LinkedNode *sort_link(LinkedNode *head) {
    if (head == NULL || head->next == NULL) {
        return head;
    } else {
        LinkedNode *front = head;
        LinkedNode *back;
        split_halves(head, &back);

        LinkedNode *left_sorted = sort_link(front);
        LinkedNode *right_sorted = sort_link(back);

        LinkedNode *result = merge_link(left_sorted, right_sorted);

        return result;
    }
}

int link_len(LinkedNode *head) {
    int len = 0;
    for (LinkedNode *node = head; node != NULL; node = node->next, len++);
    return len;
}

void free_link_pool(LinkedNode *pool) {
    free(pool);
}
