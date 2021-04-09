//
// Created by zbh on 2021/4/5.
//

#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "gc.h"
#include "os_spec.h"

#define PRINT_GC_TIME 0
#define PRINT_GC_EXPAND 1


struct HashEntryPool {
    size_t index;
    size_t capacity;
    HashEntry *pool;
};

struct LinkPool {
    size_t index;
    size_t capacity;
    HashLink *pool;
};

struct MapEntryPool {
    size_t index;
    size_t capacity;
    MapEntry *pool;
};

struct HashEntryPool *hashEntryPool;
struct LinkPool *linkPool;
struct MapEntryPool *mapEntryPool;

tp_int inner_allocate(tp_int length) {
    length = MEM_ALIGN(length);
    if (heap_counter + length < MEMORY_SIZE) {
        tp_int cur = heap_counter;
        memset(MEMORY + cur, 0, length);
        heap_counter += length;
        return cur;
    } else return -1;
}

void create_heap(tp_int heap_begins) {
    heap_counter = heap_begins;

    hashEntryPool = malloc(sizeof(struct HashEntryPool));
    hashEntryPool->capacity = MEMORY_SIZE / 512;
    hashEntryPool->index = 0;
    hashEntryPool->pool = malloc(hashEntryPool->capacity * sizeof(HashEntry));

    linkPool = malloc(sizeof(struct LinkPool));
    linkPool->capacity = MEMORY_SIZE / 512;
    linkPool->index = 0;
    linkPool->pool = malloc(linkPool->capacity * sizeof(HashLink));

    mapEntryPool = malloc(sizeof(struct MapEntryPool));
    mapEntryPool->capacity = MEMORY_SIZE / 512;
    mapEntryPool->index = 0;
    mapEntryPool->pool = malloc(mapEntryPool->capacity * sizeof(MapEntry));
}

void free_heap() {
    free(hashEntryPool->pool);
    free(hashEntryPool);
    free(linkPool->pool);
    free(linkPool);
    free(mapEntryPool->pool);
    free(mapEntryPool);
}

HashEntry *create_hash_entry() {
    HashEntry **pool = &hashEntryPool->pool;
    HashEntry *entry = &(*pool)[hashEntryPool->index++];
    if (hashEntryPool->index == hashEntryPool->capacity) {
        size_t curPoolSize = sizeof(HashEntry) * hashEntryPool->capacity;
        hashEntryPool->pool = realloc(hashEntryPool->pool, curPoolSize * 2);
        hashEntryPool->capacity *= 2;
        if (PRINT_GC_EXPAND) printf("Hash entry pool expanded to %d\n", hashEntryPool->capacity);
    }
    return entry;
}

HashLink *create_hash_link() {
    HashLink **pool = &linkPool->pool;
    HashLink *link = &(*pool)[linkPool->index++];
    if (linkPool->index == linkPool->capacity) {
        size_t curPoolSize = sizeof(HashLink) * linkPool->capacity;
        linkPool->pool = realloc(linkPool->pool, curPoolSize * 2);
        linkPool->capacity *= 2;
        if (PRINT_GC_EXPAND) printf("Hash link pool expanded to %d\n", linkPool->capacity);
    }
    return link;
}

MapEntry *create_map_entry() {
    MapEntry **pool = &mapEntryPool->pool;
    MapEntry *entry = &(*pool)[mapEntryPool->index++];
    if (mapEntryPool->index == mapEntryPool->capacity) {
        size_t curPoolSize = sizeof(MapEntry) * mapEntryPool->capacity;
        mapEntryPool->pool = realloc(mapEntryPool->pool, curPoolSize * 2);
        mapEntryPool->capacity *= 2;
        if (PRINT_GC_EXPAND) printf("Map entry pool expanded to %d\n", mapEntryPool->capacity);
    }
    return entry;
}

tp_int heap_allocate(tp_int length) {
    tp_int res = inner_allocate(length);
    if (res == -1) {
        gc();
        res = inner_allocate(length);
        if (res == -1) {
            fprintf(stderr, "Not enough heap space to heap_allocate %lld. Available memory %lld. \n",
                    (int_fast64_t) length,
                    (int_fast64_t) (MEMORY_SIZE - heap_counter));
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
        entry = create_hash_entry();
        entry->key = obj_addr;
        entry->key1 = obj_len;
        entry->key2 = obj_type;
        entry->value = create_hash_link();
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
                HashLink *new_link = create_hash_link();
                new_link->value = ptr_addr;
                new_link->parent = parent_array;
                new_link->next = entry->value;
                entry->value = new_link;  // insert at first
                return;
            }
            entry = entry->next;
        }
        HashEntry *new_entry = create_hash_entry();
        new_entry->key = obj_addr;
        new_entry->key1 = obj_len;
        new_entry->key2 = obj_type;
        new_entry->value = create_hash_link();
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
    tp_int object_addr = bytes_to_int(MEMORY + ptr_addr);
    if (object_addr == 0) return;  // NULL pointer
    if (object_addr < heap_start) return;  // Not a heap object
    if (type_code == OBJECT_CODE) {
        tp_int class_ptr = bytes_to_int(MEMORY + object_addr);
        tp_int object_len = bytes_to_int(MEMORY + object_addr + OBJECT_BYTE_LENGTH_POS);
        insert_table(table, object_addr, object_len, type_code, ptr_addr, parent);
        tp_int field_array_addr = bytes_to_int(MEMORY + class_ptr) + CLASS_FIELD_ARRAY_POS;
        tp_int field_array_ptr = bytes_to_int(MEMORY + field_array_addr);
        for (tp_int field_pos = 0; field_pos < object_len; field_pos += INT_PTR_LEN) {
            tp_int field_addr = object_addr + field_pos;
            tp_int field_code = MEMORY[field_array_ptr + ARRAY_HEADER_LEN + field_pos / INT_PTR_LEN];
            mark_one(table, field_addr, field_code, object_addr);
        }
    } else if (type_code == ARRAY_CODE) {
//        printf("array %d\n", object_addr);
        tp_int array_length = bytes_to_int(MEMORY + object_addr);
        tp_int array_ele_code = bytes_to_int(MEMORY + object_addr + INT_PTR_LEN);
        tp_int ele_len = size_of_type(array_ele_code);
        tp_int array_byte_length = array_length * ele_len + ARRAY_HEADER_LEN;
        tp_int occupation = MEM_ALIGN(array_byte_length);
//        printf("ele length %d, arr_length %d, %d, occupy %d\n",
//               ele_len, array_length, array_byte_length, occupation);
        insert_table(table, object_addr, occupation, type_code, ptr_addr, parent);
        for (tp_int index = 0; index < array_length; ++index) {
            tp_int ptr_addr_in_arr = object_addr + ARRAY_HEADER_LEN + index * ele_len;
            mark_one(table, ptr_addr_in_arr, array_ele_code, object_addr);
        }
    }
}

void mark(HashTable *marked) {
    tp_int addr = 1 + INT_PTR_LEN;  // begin of stack
//    printf("Active functions: %d\n", call_p);

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
            mark_one(marked, addr, type_code, 0);
        }
        addr = func_pure_stack_end + type_push;
    }

//    print_table(marked, "objPtr", "objLen", "objCode", "pointers");
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
        MapEntry *new_entry = create_map_entry();
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
        MapEntry *new_entry = create_map_entry();
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
    free(map->array);
    free(map);
}

void sweep(HashTable *marked) {
    size_t remain = marked->size;
    tp_int addr = heap_start;

    HashMap *trans_map = create_map(HASH_TABLE_SIZE);  // new_pos: old_pos
    HashMap *inv_trans_map = create_map(HASH_TABLE_SIZE);  // old_pos: new_pos

    // move memory and create relation map
    tp_int new_addr = heap_start;
    while (remain > 0) {
        HashEntry *entry = get_table(marked, addr);
        if (entry != NULL) {
            tp_int move_len = entry->key1;
            memmove(MEMORY + new_addr, MEMORY + addr, move_len);
//            printf("Moved length %d from %d to %d, real_len %d\n", move_len, addr, new_addr, entry->key1);
            insert_map(trans_map, new_addr, addr);
            insert_map(inv_trans_map, addr, new_addr);
            new_addr += move_len;
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
            HashEntry *old_pointers = get_table(marked, head->value);
            for (HashLink *link = old_pointers->value; link != NULL; link = link->next) {
                if (link->parent == 0) {
//                    printf("replaced ptr %d from %d to %d!\n",
//                           link->value, bytes_to_int(MEMORY + link->value), new_ptr);
                    int_to_bytes(MEMORY + link->value, new_ptr);
                } else {
                    // also modify pointers in heap arrays
                    tp_int parent_new_pos = get_map(inv_trans_map, link->parent);
                    tp_int pos_from_parent_head = link->value - link->parent;
//                    printf("replaced ptr in parent %d from %d to %d!\n",
//                           link->value, bytes_to_int(MEMORY + parent_new_pos + pos_from_parent_head), new_ptr);
                    int_to_bytes(MEMORY + parent_new_pos + pos_from_parent_head, new_ptr);
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
    if (PRINT_GC_TIME)
        tp_printf("heap counter before gc %d\n", heap_counter);

    hashEntryPool->index = 0;
    linkPool->index = 0;
    mapEntryPool->index = 0;
    HashTable *marked = create_table(HASH_TABLE_SIZE);

    mark(marked);
    sweep(marked);

    free_table(marked);
    tp_int end_time = get_time();

    if (PRINT_GC_TIME) {
        tp_printf("heap counter after gc %d\n", heap_counter);
        tp_printf("Gc time: %d\n", end_time - st_time);
    }
}

