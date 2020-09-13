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

    def __str__(self):
        return self.type_name

    def __repr__(self):
        return self.__str__()


class PointerType(Type):
    def __init__(self, base: Type):
        super().__init__(util.PTR_LEN)

        self.base = base

    def weak_convertible(self, left_tar_type):
        if isinstance(left_tar_type, BasicType) and left_tar_type.type_name == "int":
            return True
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


class FuncType(CallableType):
    def __init__(self, param_types, rtype):
        super().__init__(param_types, rtype)


class NativeFuncType(CallableType):
    def __init__(self, param_types, rtype):
        super().__init__(param_types, rtype)


class StructType(Type):
    def __init__(self, name: str, file_path: str, members: dict, length):
        super().__init__(length)

        self.name = name
        self.file_path = file_path  # where this struct is defined, avoiding conflict struct def'ns in non-export part
        self.members = members  # {name: (position, type)}

    def __eq__(self, other):
        return isinstance(other, StructType) and self.name == other.name and self.file_path == other.file_path

    def __str__(self):
        return "StructType(" + util.name_with_path(self.name, self.file_path) + ")"


# class MemoryArrayType(Type):
#     def __init__(self, ele_type: Type, num_ele=-1):
#         super().__init__(ele_type.memory_length() * num_ele)
#
#         self.ele_type = ele_type
#         self.num_ele = num_ele
#
#     def strong_convertible(self, left_tar_type):
#         return self == left_tar_type or (isinstance(left_tar_type, MemoryArrayType) and )
#
#     def __eq__(self, other):
#         return isinstance(other, MemoryArrayType) and self.ele_type == other.ele_type and self.num_ele == other.num_ele
#
#     def __str__(self):
#         if self.num_ele >= 0:
#             return f"{self.ele_type}[{self.num_ele}]"
#         else:
#             return f"{self.ele_type}[]"


class ArrayType(Type):
    def __init__(self, ele_type: Type):
        super().__init__(util.PTR_LEN)

        self.ele_type = ele_type

    def __str__(self):
        return f"{self.ele_type}[]"

    def __eq__(self, other):
        return isinstance(other, ArrayType) and self.ele_type == other.ele_type


TYPE_INT = BasicType("int", util.INT_LEN)
TYPE_FLOAT = BasicType("float", util.FLOAT_LEN)
TYPE_CHAR = BasicType("char", util.CHAR_LEN)
TYPE_BYTE = BasicType("byte", 1)
TYPE_VOID = BasicType("void", 0)

TYPE_CHAR_ARR = ArrayType(TYPE_CHAR)

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
}
