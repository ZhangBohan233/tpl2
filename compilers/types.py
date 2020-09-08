import compilers.util as util


class Type:
    def __init__(self, length: int):
        self.length = length

    def convert_able(self, left_tar_type):
        return self == left_tar_type  # todo:

    def is_void(self):
        return self.length == 0


class BasicType(Type):
    def __init__(self, type_name: str, length: int):
        super().__init__(length)

        self.type_name = type_name

    def __eq__(self, other):
        return isinstance(other, BasicType) and other.type_name == self.type_name

    def __str__(self):
        return "Type(" + self.type_name + ")"

    def __repr__(self):
        return self.__str__()


class PointerType(Type):
    def __init__(self, base: Type):
        super().__init__(util.PTR_LEN)

        self.base = base


class CallableType(Type):
    def __init__(self, param_types, rtype):
        super().__init__(util.PTR_LEN)

        self.param_types: [Type] = param_types
        self.rtype: Type = rtype


class FuncType(CallableType):
    def __init__(self, param_types, rtype):
        super().__init__(param_types, rtype)


class NativeFuncType(CallableType):
    def __init__(self, param_types, rtype):
        super().__init__(param_types, rtype)


TYPE_INT = BasicType("int", util.INT_LEN)
TYPE_FLOAT = BasicType("float", util.FLOAT_LEN)
TYPE_CHAR = BasicType("char", util.CHAR_LEN)
TYPE_VOID = BasicType("void", 0)


NATIVE_FUNCTIONS = {
    "print_int": (1, NativeFuncType([TYPE_INT], TYPE_VOID)),
    "println_int": (2, NativeFuncType([TYPE_INT], TYPE_VOID)),
    "clock": (3, NativeFuncType([], TYPE_INT))
}