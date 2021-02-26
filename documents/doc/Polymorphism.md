# Polymorphism

## Function Polymorphism

TPL supports syntax that functions with different parameters share a same name.
The actual function that to be called is determined at compile type, by the type of arguments.

For primitive parameters, only the exact match is accounted.
```
fn foo(x: int) void {
    cprintln("int");
}
fn foo(x: float) void {
    cprintln("float");
}
```
Calling `foo(1)` would prints out `int` because the argument is type `int`.
Calling `foo('a')` would not compile because `foo(char)` is not defined.

For object parameters, the function that has the minimum positive _**distance**_ parameters with the 
actual arguments is called.

The _**distance**_ of a single parameter-argument pair is defined by:
1. `-1` if Inconsistent
2. `0` if param type is equal to arg type
3. The index of parameter's class in the MRO of argument's class, if it extends `*Object`

The actual calling function minimizes the sum of _**distance**_ of all parameter-arguments.

If two functions have the same _**distance**_ sum, the code would not compile because the call is ambiguous.
