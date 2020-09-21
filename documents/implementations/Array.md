# Arrays

Notes: 
* let `PTR_LEN` = byte length of a pointer
* let `INT_LEN` = byte length of an int

### Structure
* An array stores a continuous value collection in memory.
* An array of type `T` with size `n` occupies `sizeof(T) * n + INT_LEN` bytes
in memory
* High dimensional arrays only contain an array of pointers to its direct
elements. For example `int[][]` is an array consists of pointers
to `int[]`

### A typical example:
```
a: int[][] = int[2][3];
a[0][0] = 128;
a[0][1] = 129;
a[0][2] = 130;
a[1][0] = 131;
a[1][1] = 132;
a[1][2] = 133;
```

In a typical 32 bits TVM, assume the starting address is 0, then the 
memory structure should be like
```
4 0 0 0 | 2 0 0 0 | 16 0 0 0 | 32 0 0 0 | 3 0 0 0 | 128 0 0 0 
| 129 0 0 0 | 130 0 0 0 | 3 0 0 0 | 131 0 0 0 | 132 0 0 0 
| 133 0 0 0
```
Description:
```
var a | size 2 | ptr to 1st inner array | ptr to 2nd inner array |
size 3 | v0 | v1 | v2 | size 3 | v4 | v5 | v6 
```

