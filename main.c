#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "tvm/tvm.h"


/*
 * Flags:
 *
 * -e, --exit:       print exit value
 * -m, --mem:        print stack, global, literal, heap memory
 * -fm, --full-mem:  print all memory
 */

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "No input file specified.");
        return 1;
    }

    int p_memory = 0;
    int p_exit = 0;
    char *file_name = argv[1];

    int vm_args_begin = 0;

    for (int i = 1; i < argc; i++) {
        char *arg = argv[i];
        if (arg[0] == '-') {
            if (strcmp(arg, "-e") == 0 || strcmp(arg, "--exit") == 0)
                p_exit = 1;
            else if (strcmp(arg, "-m") == 0 || strcmp(arg, "--mem") == 0)
                p_memory = 1;
            else if (strcmp(arg, "-fm") == 0 || strcmp(arg, "--full_mem") == 0)
                p_memory = 2;
            else
                printf("Unknown flag: -%c", arg[1]);
        } else {
            file_name = arg;
            vm_args_begin = i;
            break;
        }
    }

    int vm_argc = argc - vm_args_begin;
    char **vm_argv = malloc(sizeof(char **) * vm_argc);
    for (int i = vm_args_begin; i < argc; i++) {
        vm_argv[i - vm_args_begin] = argv[i];
    }

    tvm_run(p_memory, p_exit, file_name, vm_argc, vm_argv);

    free(vm_argv);

    return 0;
}
