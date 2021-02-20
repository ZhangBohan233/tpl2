import collections

import compilers.util as util
import compilers.errors as errs


class Type:
    def __init__(self, length: int):
        self.length = length

    def memory_length(self):
        return self.length

    def strong_convertible(self, left_tar_type):
        """
        This method returns True iff self can be converted to the 'left_tar_type' without warning.

        :param left_tar_type:
        :return:
        """
        return self == left_tar_type

    def weak_convertible(self, left_tar_type):
        """
        This method returns True iff self can be converted to the 'left_tar_type', but a warning is produced.

        Note that this method does not necessarily returns True if strong_convertible returns True.

        :param left_tar_type:
        :return:
        """
        return self.strong_convertible(left_tar_type)

    def convertible_to(self, left_tar_type, lf):
        """
        Returns True if strong_convertible or weak_convertible returns True.

        Prints warning message if strong_convertible returns False, but weak_convertible returns True.

        :param left_tar_type
        :param lf
        :return:
        """
        if self.strong_convertible(left_tar_type):
            return True
        elif self.weak_convertible(left_tar_type):
            print("Warning: implicit conversion from {} to {}. {}".format(self, left_tar_type, lf))
            return True
        else:
            return False

    def check_convertibility(self, left_tar_type, lf) -> None:
        if not self.convertible_to(left_tar_type, lf):
            raise errs.TplCompileError(f"Cannot convert '{self}' to '{left_tar_type}'. ", lf)

    def is_void(self):
        return self.length == 0

    def __repr__(self):
        return self.__str__()


class BasicType(Type):
    def __init__(self, type_name: str, length: int):
        super().__init__(length)

        self.type_name = type_name

    def weak_convertible(self, left_tar_type: Type):
        if self.type_name == "int" and isinstance(left_tar_type, PointerType):
            return True
        else:
            return super().weak_convertible(left_tar_type)

    def __eq__(self, other):
        return isinstance(other, BasicType) and other.type_name == self.type_name

    def __hash__(self):
        return hash(self.type_name)

    def __str__(self):
        return self.type_name

    def __repr__(self):
        return self.__str__()


class PointerType(Type):
    def __init__(self, base: Type):
        super().__init__(util.PTR_LEN)

        self.base = base

    def strong_convertible(self, left_tar_type):
        if self == TYPE_VOID_PTR:
            return isinstance(left_tar_type, PointerType) or isinstance(left_tar_type, ArrayType)
        elif left_tar_type == TYPE_VOID_PTR:
            return True
        elif isinstance(left_tar_type, PointerType):
            return self.base.strong_convertible(left_tar_type.base)
        else:
            return super().strong_convertible(left_tar_type)

    def weak_convertible(self, left_tar_type):
        if isinstance(left_tar_type, BasicType) and left_tar_type.type_name == "int":
            return True
        elif isinstance(left_tar_type, PointerType):
            return self.base.weak_convertible(left_tar_type.base)
        else:
            return super().weak_convertible(left_tar_type)

    def __eq__(self, other):
        return isinstance(other, PointerType) and self.base == other.base

    def __str__(self):
        return "*" + str(self.base)

    def __repr__(self):
        return self.__str__()


class CompileTimeFunctionType(Type):
    def __init__(self, name, rtype: Type):
        super().__init__(0)

        self.name = name
        self.rtype = rtype

    def memory_length(self):
        raise errs.TplCompileError(f"Compile time function '{self.name}' does not occupy memory. ")

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, CompileTimeFunctionType) and self.name == other.name


class CallableType(Type):
    def __init__(self, param_types, rtype):
        super().__init__(util.PTR_LEN)

        self.param_types: [Type] = param_types
        self.rtype: Type = rtype

    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
               self.param_types == other.param_types and \
               self.rtype == other.rtype

    def __str__(self):
        return "{}({} -> {})".format(self.__class__.__name__, self.param_types, self.rtype)

    def __repr__(self):
        return self.__str__()


class FuncType(CallableType):
    def __init__(self, param_types, rtype):
        super().__init__(param_types, rtype)

    def strong_convertible(self, left_tar_type):
        if isinstance(left_tar_type, FuncType):
            if len(self.param_types) == len(left_tar_type.param_types):
                if self.rtype.strong_convertible(left_tar_type.rtype):
                    for i in range(len(self.param_types)):
                        if not self.param_types[i].strong_convertible(left_tar_type.param_types[i]):
                            return False
                    return True
        return False


class MethodType(FuncType):
    def __init__(self, param_types, rtype, def_class):
        super().__init__(param_types, rtype)

        self.defined_class = def_class

    def __str__(self):
        return "method " + super().__str__()

    def copy(self):
        return MethodType(self.param_types.copy(), self.rtype, self.defined_class)


class NativeFuncType(CallableType):
    def __init__(self, param_types, rtype):
        super().__init__(param_types, rtype)


class ClassType(Type):
    def __init__(self, name: str, class_ptr: int, file_path: str, direct_sc: list, templates: list,
                 super_generics_map: dict):
        super().__init__(0)

        self.name = name
        self.class_ptr = class_ptr
        self.file_path = file_path  # where this class is defined, avoiding conflict struct def'ns in non-export part
        self.name_with_path = util.class_name_with_path(self.name, self.file_path)
        self.direct_superclasses = direct_sc
        self.mro: list = None  # Method resolution order, ranked from closest to farthest
        self.templates = templates  # list of Generic
        self.method_rank = []  # keep track of all method names in order
        # this dict records all callable methods in this class, including methods in its superclass
        # methods with same name must have the same id, i.e. overriding methods have the same id
        self.methods = {}  # name: (method_id, func_ptr, func_type)
        self.fields = collections.OrderedDict()  # OrderedDict, name: (position, type)
        # records mapping for superclass
        # e.g. class A<K, V>, class B<X>(A<X, Object>) => {A: {"K": "X", "V": Object}}
        self.super_generics_map = super_generics_map

    def full_name(self):
        return self.name_with_path

    def has_field(self, name: str) -> bool:
        for mro_t in self.mro:
            if name in mro_t.fields:
                return True
        return False

    def find_field(self, name: str, lf) -> (int, Type):
        for mro_t in self.mro:
            if name in mro_t.fields:
                return mro_t.fields[name]
        raise errs.TplCompileError(f"Class {self.name} does not have field '{name}'. ", lf)

    def find_method(self, name: str, lf) -> (int, int, MethodType):
        if name in self.methods:
            return self.methods[name]
        else:
            raise errs.TplCompileError(f"Class {self.name} does not have method '{name}'. ", lf)

    def strong_convertible(self, left_tar_type):
        if isinstance(left_tar_type, Generic):
            return self.strong_convertible(left_tar_type.max_t)
        if isinstance(left_tar_type, ClassType):
            for t in self.mro:
                if t == left_tar_type:
                    return True
        else:
            return super().strong_convertible(left_tar_type)

    def superclass_of(self, child_t: Type):
        if isinstance(child_t, ClassType):
            for t in child_t.mro:
                if self == t:
                    return True
        return False

    def __eq__(self, other):
        return isinstance(other, ClassType) and self.name == other.name and self.file_path == other.file_path

    def __str__(self):
        return "ClassType(" + util.class_name_with_path(self.name, self.file_path) + ")"

    def __hash__(self):
        return self.name_with_path.__hash__()

    def __repr__(self):
        return self.__str__()


class GenericType(Type):
    def __init__(self, base, generics: dict):
        super().__init__(base.length)

        self.base = base
        self.generics = generics

    def __str__(self):
        return f"{self.base}<{self.generics}>"

    def strong_convertible(self, left_tar_type):
        if isinstance(left_tar_type, GenericType):
            if self.base.strong_convertible(left_tar_type.base):
                if len(self.generics) == len(left_tar_type.generics):
                    for key in self.generics:
                        if key in left_tar_type.generics:
                            if self.generics[key].strong_convertible(left_tar_type.generics[key]):
                                continue
                        break
                    return True
        return False


class GenericClassType(GenericType):
    def __init__(self, base: ClassType, generic: dict):
        super().__init__(base, generic)


class Generic(Type):
    def __init__(self, name: str, max_t: ClassType):
        super().__init__(max_t.length)

        self._name = name
        self.max_t = max_t

    def strong_convertible(self, left_tar_type):
        return self.max_t.strong_convertible(left_tar_type)

    def simple_name(self):
        return self._name

    def __eq__(self, other):
        return isinstance(other, Generic) and self._name == other._name

    def __str__(self):
        return f"{self._name}: {self.max_t}"


class ArrayType(Type):
    def __init__(self, ele_type: Type):
        super().__init__(util.PTR_LEN)

        self.ele_type = ele_type

    def strong_convertible(self, left_tar_type):
        if left_tar_type == TYPE_VOID_PTR:
            return True
        else:
            return super().strong_convertible(left_tar_type)

    def __str__(self):
        return f"{self.ele_type}[]"

    def __hash__(self):
        return hash(self.ele_type) + 1

    def __eq__(self, other):
        return isinstance(other, ArrayType) and self.ele_type == other.ele_type


def is_generic(t: Type) -> bool:
    if isinstance(t, PointerType):
        return is_generic(t.base)
    return isinstance(t, Generic)


def replace_generic_with_real(t: Type, real_generics: dict) -> Type:
    if isinstance(t, PointerType):
        return PointerType(replace_generic_with_real(t.base, real_generics))
    elif isinstance(t, Generic):
        return real_generics[t.simple_name()]
    else:
        raise errs.TplCompileError("Unexpected error.")


def index_in_generic_list(name: str, generics: list) -> int:
    for i in range(len(generics)):
        if name == generics[i].simple_name():
            return i
    return -1


TYPE_INT = BasicType("int", util.INT_LEN)
TYPE_FLOAT = BasicType("float", util.FLOAT_LEN)
TYPE_CHAR = BasicType("char", util.CHAR_LEN)
TYPE_BYTE = BasicType("byte", 1)
TYPE_VOID = BasicType("void", 0)

TYPE_CHAR_ARR = ArrayType(TYPE_CHAR)
TYPE_STRING_ARR = ArrayType(TYPE_CHAR_ARR)
TYPE_VOID_PTR = PointerType(TYPE_VOID)

PRIMITIVE_TYPES = {"int": TYPE_INT, "float": TYPE_FLOAT, "char": TYPE_CHAR, "byte": TYPE_BYTE, "void": TYPE_VOID}

NATIVE_FUNCTIONS = {
    "print_int": (1, NativeFuncType([TYPE_INT], TYPE_VOID)),
    "println_int": (2, NativeFuncType([TYPE_INT], TYPE_VOID)),
    "clock": (3, NativeFuncType([], TYPE_INT)),
    "print_char": (4, NativeFuncType([TYPE_CHAR], TYPE_VOID)),
    "println_char": (5, NativeFuncType([TYPE_CHAR], TYPE_VOID)),
    "print_float": (6, NativeFuncType([TYPE_FLOAT], TYPE_VOID)),
    "println_float": (7, NativeFuncType([TYPE_FLOAT], TYPE_VOID)),
    "print_str": (8, NativeFuncType([TYPE_CHAR_ARR], TYPE_VOID)),
    "println_str": (9, NativeFuncType([TYPE_CHAR_ARR], TYPE_VOID)),
    "malloc": (10, NativeFuncType([TYPE_INT], TYPE_VOID_PTR)),
    "free": (11, NativeFuncType([TYPE_VOID_PTR], TYPE_VOID)),
    "heap_array": (12, NativeFuncType([TYPE_INT, ArrayType(TYPE_INT)], TYPE_VOID_PTR))
}
