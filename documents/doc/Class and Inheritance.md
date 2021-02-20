# Class and Inheritance

### Generic class inheritance

A class can inherit another generic class
```
class Parent<K, V> { ... }
class Child<T>(Parent<T, Object>) { ... }
```

Note that a class can only extend one generic class.

A counter example is:
```
class Thing { ... }
class A<T> { ... }
class B<V> { ... }
class C<K, V>(A<
```
