import compilers.util as util


class Type:
    def __init__(self, length: int):
        self.length = length

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
        return "Type(" + self.type_name + ")"

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

    def __str__(self):
        return "*" + str(self.base)

    def __repr__(self):
        return self.__str__()


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
