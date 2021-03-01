# Class and Inheritance

## Inheritance

A class can inherit other classes, as long as the inheritance order is compatible.

The syntax for class inheritance is `class ClassName(ParentClass1, ParentClass2, ...) { ... }`

A class with no parent class specified will automatically extends `Object`, unless it is `Object` itself.

## Generic class inheritance

A class can inherit another generic class
```
class Parent<K, V> { ... }
class Child<T>(Parent<T, Object>) { ... }
```

## Method

Functions defined inside class body are called method.

The instance is accessed in methods' body via keyword `this`.

The keyword `this` may be defined as the first parameter in methods. This parameter be type of the pointer to 
instances of the class whether this method is defined in.
The compiler would automatically insert parameter `this` if the programmer does not.

Example codes:
```
class Parent {
    value: int;
    
    // 'this: *Parent' is inserted automatically before 'val: int'
    fn __new__(val: int) void {
        // 'super.__new__()' is inserted automatically here, calling Object.__new__
        this.value = val;
    }
    
    // polymorphic constructor
    fn __new__() void {
        this.__new__(42);
    }
}

class Child(Parent) {
    fn __new__(this: *Child) void {
        super.__new__();
    }
}

fn main() int {
    child: *Child = new Child();
    return child.value;  // returns 42
}
```

## Constructor

A class may define constructor method(s) named `__new__`. If the programmer does not specify a `__new__` method,
the compiler would automatically define a `__new__(this)` in this class.

For all constructors except the constructor of class `Object`, a `super.__new__(...)` call is required at the 
beginning of the constructors' body. If the programmer does not do so, the compiler would automatically insert 
a super call, with no extra arguments.

## Method Call

There are generally twos ways to call a method.

1. Call via instance, with the syntax `instance.method(args...)`
2. Call via class, with the syntax `Clazz.method(instance, args...)`
