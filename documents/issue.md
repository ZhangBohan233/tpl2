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

## Macro

### ISSUE M01
exportmacro does not work
