# Class and Inheritance

### Generic class inheritance

A class can inherit another generic class
```
class Parent<K, V> { ... }
class Child<T>(Parent<T, Object>) { ... }
```

