//
// Created by zbh on 2021/4/5.
//

#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "gc.h"
#include "os_spec.h"

tp_int inner_allocate(tp_int length) {
    if (heap_counter + length < MEMORY_SIZE) {
        tp_int cur = heap_counter;
        heap_counter += length;
        return cur;
    } else return -1;
}

void create_heap(tp_int heap_begins) {
    heap_counter = heap_begins;
}

tp_int heap_allocate(tp_int length) {
    tp_int res = inner_allocate(length);
    if (res == -1) {
        gc();
        res = inner_allocate(length);
        if (res == -1) {
            fprintf(stderr, "Not enough heap space to heap_allocate %lld.", (int_fast64_t) length);
            return -1;
        }
    }
    return res;
}

HashTable *create_table(size_t capacity) {
    HashEntry **array = calloc(capacity, sizeof(HashEntry *));
    HashTable *table = malloc(sizeof(HashTable));
    table->array = array;
    table->size = 0;
    table->capacity = capacity;
    return table;
}

void free_table(HashTable *table) {
    for (int i = 0; i < table->capacity; ++i) {
        for (HashEntry *head = table->array[i]; head != NULL;) {
            for (HashLink *link = head->value; link != NULL;) {
                HashLink *next_link = link->next;
                free(link);
                link = next_link;
            }
            HashEntry *next = head->next;
            free(head);
            head = next;
        }
    }
    free(table->array);
    free(table);
}

void print_table(HashTable *table, char *key_name, char *key1_name, char *key2_name, char *value_name) {
    printf("Table of size %d: {\n", table->size);
    for (int i = 0; i < table->capacity; ++i) {
        for (HashEntry *head = table->array[i]; head != NULL; head = head->next) {
            tp_printf("    %s: %d, %s: %d, %s, %d, %s: ",
                      key_name, head->key, key1_name, head->key1, key2_name, head->key2, value_name);
            for (HashLink *link = head->value; link != NULL; link = link->next) {
                tp_printf("%d:", link->value);
                printf("%d, ", link->parent);
            }
            printf("\n");
        }
    }
    printf("}\n");
}

size_t hash(tp_int key, size_t array_capacity) {
    return (key >> SHIFT) * 31 % array_capacity;
}

/*
 * In the pointer table, obj_addr is object address, values are pointer addresses
 */
void insert_table(HashTable *table, tp_int obj_addr, tp_int obj_len, tp_int obj_type, tp_int ptr_addr,
                  tp_int parent_array) {
//    printf("obj_addr: %d, ptr_addr: %d, length: %d\n", obj_addr, ptr_addr, obj_len);
    if (obj_addr == 0) return;  // pointer to null
    unsigned int index = hash(obj_addr, table->capacity);
    HashEntry *entry = table->array[index];
    if (entry == NULL) {
        entry = malloc(sizeof(HashEntry));
        entry->key = obj_addr;
        entry->key1 = obj_len;
        entry->key2 = obj_type;
        entry->value = malloc(sizeof(HashLink));
        entry->value->value = ptr_addr;
        entry->value->parent = parent_array;
        entry->value->next = NULL;
        entry->next = NULL;
        table->array[index] = entry;
        table->size++;
    } else {
        while (entry != NULL) {
            if (entry->key == obj_addr) {
                HashLink *link = entry->value;
                while (link != NULL) {
                    if (link->value == ptr_addr) return;  // duplicate pointer
                    link = link->next;
                }
                HashLink *new_link = malloc(sizeof(HashLink));
                new_link->value = ptr_addr;
                new_link->parent = parent_array;
                new_link->next = entry->value;
                entry->value = new_link;  // insert at first
                return;
            }
            entry = entry->next;
        }
        HashEntry *new_entry = malloc(sizeof(HashEntry));
        new_entry->key = obj_addr;
        new_entry->key1 = obj_len;
        new_entry->key2 = obj_type;
        new_entry->value = malloc(sizeof(HashLink));
        new_entry->value->value = ptr_addr;
        new_entry->value->parent = parent_array;
        new_entry->value->next = NULL;
        new_entry->next = table->array[index];
        table->array[index] = new_entry;
        table->size++;
    }
}

HashEntry *get_table(HashTable *table, tp_int key) {
    size_t index = hash(key, table->capacity);
    for (HashEntry *entry = table->array[index]; entry != NULL; entry = entry->next) {
        if (entry->key == key) return entry;
    }
    return NULL;
}

void mark_one(HashTable *table, tp_int ptr_addr, tp_int type_code, tp_int parent) {
    if (bytes_to_int(MEMORY + ptr_addr) == 0) return;  // NULL pointer
    if (type_code == OBJECT_CODE) {
        tp_int object_addr = bytes_to_int(MEMORY + ptr_addr);
        tp_int class_ptr = bytes_to_int(MEMORY + object_addr);
        tp_int object_len = bytes_to_int(MEMORY + object_addr + OBJECT_BYTE_LENGTH_POS);
        insert_table(table, object_addr, object_len, type_code, ptr_addr, parent);
        tp_int field_array_addr = bytes_to_int(MEMORY + class_ptr) + CLASS_FIELD_ARRAY_POS;
        tp_int field_array_ptr = bytes_to_int(MEMORY + field_array_addr);
        for (tp_int field_pos = 0; field_pos < object_len; field_pos += INT_PTR_LEN) {
            tp_int field_addr = object_addr + field_pos;
            tp_int field_code = MEMORY[field_array_ptr + ARRAY_HEADER_LEN + field_pos / INT_PTR_LEN];
            mark_one(table, field_addr, field_code, 0);
        }
    } else if (type_code == ARRAY_CODE) {
        tp_int array_addr = bytes_to_int(MEMORY + ptr_addr);
//        printf("array %d\n", array_addr);
        tp_int array_length = bytes_to_int(MEMORY + array_addr);
        tp_int array_ele_code = bytes_to_int(MEMORY + array_addr + INT_PTR_LEN);
        tp_int array_byte_length = array_length * size_of_type(array_ele_code) + ARRAY_HEADER_LEN;
        insert_table(table, array_addr, array_byte_length, type_code, ptr_addr, parent);
        for (tp_int index = 0; index < array_length; ++index) {
            tp_int ptr_addr_in_arr = array_addr + ARRAY_HEADER_LEN + index * INT_PTR_LEN;
            mark_one(table, ptr_addr_in_arr, array_ele_code, array_addr);
        }
    }
}

void mark() {
    tp_int addr = 1 + INT_PTR_LEN;  // begin of stack
    printf("Active functions: %d\n", call_p);

    // loop through stack
    for (int call_id = 0; call_id < call_p; ++call_id) {
        tp_int this_stack_begin = addr;
        tp_int pure_push = bytes_to_int(MEMORY + addr);
        tp_int type_push = pure_push / INT_PTR_LEN;
        if (type_push % INT_PTR_LEN != 0) type_push = (type_push / INT_PTR_LEN + 1) * INT_PTR_LEN;
        tp_int func_pure_stack_end = addr + pure_push;
//        printf("function from %d to %d \n", this_stack_begin, func_pure_stack_end + type_push);
        for (addr += INT_PTR_LEN; addr < func_pure_stack_end; addr += INT_PTR_LEN) {
            tp_int type_code = runtime_type_abs(addr, this_stack_begin);
//            printf("type code at %d is %d\n", addr, type_code);
            mark_one(pointer_table, addr, type_code, 0);
        }
        addr = func_pure_stack_end + type_push;
    }

//    print_table(pointer_table, "objPtr", "objLen", "objCode", "pointers");
}

HashMap *create_map(size_t capacity) {
    MapEntry **array = calloc(capacity, sizeof(MapEntry*));
    HashMap *map = malloc(sizeof(HashMap));
    map->capacity = capacity;
    map->array = array;
    return map;
}

void print_map(HashMap *map) {
    printf("Map {");
    for (size_t i = 0; i < map->capacity; ++i) {
        for (MapEntry *head = map->array[i]; head != NULL; head = head->next) {
            tp_printf("%d: %d, ", head->key, head->value);
        }
    }
    printf("}\n");
}

void insert_map(HashMap *map, tp_int key, tp_int value) {
    size_t index = hash(key, map->capacity);
    MapEntry *entry = map->array[index];
    if (entry == NULL) {
        MapEntry *new_entry = malloc(sizeof(MapEntry));
        new_entry->key = key;
        new_entry->value = value;
        new_entry->next = NULL;
        map->array[index] = new_entry;
    } else {
        while (entry != NULL) {
            if (entry->key == key) {
                if (entry->value != value) {
                    fprintf(stderr, "New value conflicts with old value\n");
                }
                return;
            }
            entry = entry->next;
        }
        MapEntry *new_entry = malloc(sizeof(MapEntry));
        new_entry->key = key;
        new_entry->value = value;
        new_entry->next = map->array[index];
        map->array[index] = new_entry;
    }
}

tp_int get_map(HashMap *map, tp_int key) {
    size_t index = hash(key, map->capacity);
    for (MapEntry *entry = map->array[index]; entry != NULL; entry = entry->next) {
        if (entry->key == key) return entry->value;
    }
    return -1;
}

void free_map(HashMap *map) {
    for (int i = 0; i < map->capacity; ++i) {
        for (MapEntry *head = map->array[i]; head != NULL;) {
            MapEntry *next = head->next;
            free(head);
            head = next;
        }
    }
    free(map->array);
    free(map);
}

void sweep() {
    size_t remain = pointer_table->size;
    tp_int addr = heap_start;

    HashMap *trans_map = create_map(HASH_TABLE_SIZE);  // new_pos: old_pos
    HashMap *inv_trans_map = create_map(HASH_TABLE_SIZE);  // old_pos: new_pos

    // move memory and create relation map
    tp_int new_addr = heap_start;
    while (remain > 0) {
        HashEntry *entry = get_table(pointer_table, addr);
        if (entry != NULL) {
            memmove(MEMORY + new_addr, MEMORY + addr, entry->key1);
            insert_map(trans_map, new_addr, addr);
            insert_map(inv_trans_map, addr, new_addr);
            new_addr += entry->key1;
            remain--;
        }
        addr += INT_PTR_LEN;
    }
//    print_map(trans_map);
//    printf("Inv ");
//    print_map(inv_trans_map);

    // modify pointers
    for (size_t i = 0; i < trans_map->capacity; ++i) {
        for (MapEntry *head = trans_map->array[i]; head != NULL; head = head->next) {
            tp_int new_ptr = head->key;
            HashEntry *old_pointers = get_table(pointer_table, head->value);
            for (HashLink *link = old_pointers->value; link != NULL; link = link->next) {
                if (link->parent == 0) {
//                    printf("replaced ptr %d from %d to %d!\n",
//                           link->value, bytes_to_int(MEMORY + link->value), new_ptr);
                    int_to_bytes(MEMORY + link->value, new_ptr);
                } else {
                    // also modify pointers in heap arrays
                    tp_int arr_new_pos = get_map(inv_trans_map, link->parent);
                    tp_int pos_from_arr_head = link->value - link->parent;
//                    printf("replaced ptr in array %d from %d to %d!\n",
//                           link->value, bytes_to_int(MEMORY + arr_new_pos + pos_from_arr_head), new_ptr);
                    int_to_bytes(MEMORY + arr_new_pos + pos_from_arr_head, new_ptr);
                }
            }
        }
    }

    free_map(trans_map);
    free_map(inv_trans_map);
    heap_counter = new_addr;
}

void gc() {
    tp_int st_time = get_time();
    tp_printf("heap counter before gc %d\n", heap_counter);

    pointer_table = create_table(HASH_TABLE_SIZE);

    mark();
    sweep();

    free_table(pointer_table);
    tp_printf("heap counter after gc %d\n", heap_counter);

    tp_int end_time = get_time();
    tp_printf("Gc time: %d\n", end_time - st_time);
}

