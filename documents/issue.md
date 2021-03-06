# ISSUE

## Class and inheritance

### ~~ISSUE C01~~ FIXED
Cannot override when the declared type is the parent class
```
class A {
    ...
    fn foo() void {
        cprintln("A");
    }
}
class B {
    ...
    fn foo() void {
        cprintln("B);
    }
}
fn main() int {
    a: *A = new B();
    a.foo();  // prints "A", but should print "B"
    ...
}
```

## Array

### ISSUE A01
Heap array creation does not check valid argument.

E.g.
```
array := int[];  // should throw error but not
```

## Macro

### ~~ISSUE M01~~ FIXED
`exportmacro does` not work
