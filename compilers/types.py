import compilers.util as util
import compilers.errors as errs


class Type:
    def __init__(self, length: int):
        self.length = length

    def memory_length(self):
        """
        Returns the memory occupation of this type.

        :return:
        """
        return self.length

    def stack_length(self):
        """
        Returns the same of self.memory_length(), except for array types.

        :return:
        """
        return self.memory_length()

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

    def normal_convertible(self, left_tar_type):
        return self.strong_convertible(left_tar_type)

    def convertible_to(self, left_tar_type, lf, normal=True, weak=True):
        """
        Returns True if strong_convertible or weak_convertible returns True.

        Prints warning message if strong_convertible returns False, but weak_convertible returns True.

        :param left_tar_type
        :param lf
        :param normal whether 'normal_convertible' is counted as True
        :param weak whether 'weak_convertible' is counted as True
        :return:
        """
        if self.strong_convertible(left_tar_type):
            return True
        elif normal and self.normal_convertible(left_tar_type):
            return True
        elif normal and weak and self.weak_convertible(left_tar_type):
            util.print_warning(f"implicit conversion from {self} to {left_tar_type}.", lf)
            return True
        else:
            return False

    def check_convertibility(self, left_tar_type, lf, normal=True, weak=True) -> None:
        if not self.convertible_to(left_tar_type, lf, normal=normal, weak=weak):
            raise errs.TplCompileError(f"Cannot convert '{self}' to '{left_tar_type}'. ", lf)

    def type_name(self):
        raise errs.TplCompileError(f"Type '{self}' does not have name.")

    def is_void(self):
        return self.length == 0

    def __str__(self):
        return "Type of length " + str(self.length)

    def __repr__(self):
        return self.__str__()


class PrimitiveType(Type):
    def __init__(self, type_name: str, length: int):
        super().__init__(length)

        self.t_name = type_name

    def weak_convertible(self, left_tar_type: Type):
        if self.t_name == "int" and isinstance(left_tar_type, PointerType):
            return True
        else:
            return super().weak_convertible(left_tar_type)

    def type_name(self):
        return self.t_name

    def int_like(self):
        return self.t_name == "int" or self.t_name == "char" or self.t_name == "byte"

    def __eq__(self, other):
        return isinstance(other, PrimitiveType) and other.t_name == self.t_name

    def __hash__(self):
        return hash(self.t_name)

    def __str__(self):
        return self.t_name


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

    def normal_convertible(self, left_tar_type):
        if self.strong_convertible(left_tar_type):
            return True
        elif isinstance(left_tar_type, PointerType):
            return self.base.normal_convertible(left_tar_type.base)
        else:
            return super().normal_convertible(left_tar_type)

    def weak_convertible(self, left_tar_type):
        if isinstance(left_tar_type, PrimitiveType) and left_tar_type.t_name == "int":
            return True
        elif isinstance(left_tar_type, PointerType):
            return self.base.weak_convertible(left_tar_type.base)
        else:
            return super().weak_convertible(left_tar_type)

    def type_name(self):
        return "*" + self.base.type_name()

    def __eq__(self, other):
        return isinstance(other, PointerType) and self.base == other.base

    def __str__(self):
        return "*" + str(self.base)


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
        return type(self) == type(other) and self.name == other.name


class SpecialCtfType(CompileTimeFunctionType):
    def __init__(self, name):
        super().__init__(name, None)


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

    def normal_convertible(self, left_tar_type):
        if self.strong_convertible(left_tar_type):
            return True
        if isinstance(left_tar_type, FuncType):
            if len(self.param_types) == len(left_tar_type.param_types):
                if self.rtype.normal_convertible(left_tar_type.rtype):
                    for i in range(len(self.param_types)):
                        if not self.param_types[i].normal_convertible(left_tar_type.param_types[i]):
                            return False
                    return True
        return False


class MethodType(FuncType):
    def __init__(self, param_types, rtype, def_class,
                 is_constructor: bool, abstract: bool, const: bool, permission: int):
        super().__init__(param_types, rtype)

        self.defined_class = def_class
        self.constructor = is_constructor
        self.abstract = abstract
        self.const = const
        self.permission = permission

    def __str__(self):
        return ("abstract " if self.abstract else "") + "method " + super().__str__()

    def copy(self):
        return MethodType(self.param_types.copy(), self.rtype, self.defined_class, self.constructor,
                          self.abstract, self.const, self.permission)


class NativeFuncType(CallableType):
    def __init__(self, param_types, rtype):
        super().__init__(param_types, rtype)


class FunctionPlacer(Type):
    def __init__(self, first_t: CallableType, first_addr: int):
        super().__init__(0)

        self.poly = util.NaiveDict(params_eq)  # functions with same name | func_type: ptr

        self.add_poly(first_t, first_addr)

    def add_poly(self, type_: CallableType, addr: int):
        if type_ in self.poly:
            raise errs.TplEnvironmentError("Function already defined.")
        self.poly[type_] = addr
        # print(self.poly)

    def get_only(self):
        return self.poly.get_only()

    def get_type_and_ptr_call(self, arg_types: list, name: str, lf) -> (CallableType, int):
        try:
            return find_closet_func(self.poly, arg_types, name, False, lambda poly_d, i: poly_d.keys[i], lf)
        except errs.TplCompileError as e:
            print(name, self.poly)
            raise e

    def get_type_and_ptr_def(self, param_types: list, lf) -> (CallableType, int):
        t_addr = self.poly.get_entry_by(param_types, func_eq_params)
        if t_addr is None:
            raise errs.TplEnvironmentError(f"Cannot resolve param {param_types}. ", lf)
        return t_addr

    def __str__(self):
        return "FunctionPlacer:" + str(self.poly)


class ClassType(Type):
    def __init__(self, name: str, class_ptr: int, file_path: str, class_env, direct_sc: list, templates: list,
                 templates_map: dict, abstract: bool):
        super().__init__(0)

        self.name = name
        self.class_ptr = class_ptr
        self.file_path = file_path  # where this class is defined, avoiding conflict struct def'ns in non-export part
        self.name_with_path = util.class_name_with_path(self.name, self.file_path)
        self.class_env = class_env
        self.abstract = abstract
        self.direct_superclasses = direct_sc
        self.mro: [ClassType] = None  # Method resolution order, ranked from closest to farthest
        self.templates = templates  # list of self templates

        # keep track of all method names in order | (name, method_t)
        # note that method_t in this list is not reliable, use methods[name][method_t][...] instead
        self.method_rank = []

        # this dict records all callable methods in this class, including methods in its superclass
        # methods with same name must have the same id, i.e. overriding methods have the same id
        # note that in each NaiveDict, the key is the type of the most super method, real type is in the values
        self.methods: {str: util.NaiveDict} = {}  # name: NaiveDict{func_type: (method_id, func_ptr, func_type)}
        self.fields = {}  # name: (position, type, defined_class, const?, permission)

        # records mapping for all templates
        # e.g. class A<AT>, class B<BK, BV(Number)>(A<BK>), class D<DT>, class C<CT>(B<CT, Integer>, D<CT>) =>
        # in A: {"AT": Object}
        # in B: {"BK": Object, "BV": Number, "AT": "BK"}
        # in D: {"DT": Object}
        # in C: {"CT": Object, "BK": "CT", "BV": Integer, "AT": "BK", "DT": "CT"}
        self.templates_map = templates_map

        self.initializers = []  # nodes that will be executed in __new__

    def type_name(self):
        return self.name

    def full_name(self):
        return self.name_with_path

    def get_actual_template_name(self, template_name):
        if template_name not in self.templates_map:
            return None
        actual_tem = self.templates_map[template_name]
        if isinstance(actual_tem, str):
            return self.get_actual_template_name(actual_tem)
        else:
            return template_name

    def has_field(self, name: str) -> bool:
        for mro_t in self.mro:
            if name in mro_t.fields:
                return True
        return False

    def find_field(self, name: str, lf) -> (int, Type, Type, bool, int):
        """
        Returns (field_pos, type, defined_class, const, permission)

        :param name:
        :param lf:
        :return:
        """
        for mro_t in self.mro:
            if name in mro_t.fields:
                return mro_t.fields[name]
        raise errs.TplEnvironmentError(f"Class {self.name} does not have field '{name}'. ", lf)

    def _find_method(self, name, arg_types, lf):
        if name in self.methods:
            poly: util.NaiveDict = self.methods[name]
            return find_closet_func(poly, arg_types, name, True, lambda poly_d, i: poly_d.values[i][2], lf)[1]

        raise errs.TplEnvironmentError(f"Class {self.name} does not have method '{name}'. ", lf)

    def find_method(self, name: str, arg_types: list, lf) -> (int, int, MethodType):
        """
        Returns method_id, method_ptr, method_type

        :param name:
        :param arg_types: list of arg type, please insert None at index 0 to represent 'this', if it is not included.
        :param lf:
        :return:
        """
        if name == "__new__":
            return self.find_local_method(name, arg_types, lf)
        else:
            return self._find_method(name, arg_types, lf)

    def find_local_method(self, name: str, arg_types: list, lf) -> (int, int, MethodType):
        """
        Returns only the matching method that is defined in this class, not in superclasses.

        The mechanism is that, for example, the signature of 'hash' defined in 'Object' is 'hash(this: *Object) int',
        but in 'String' is 'hash(this: *String) int'. Checking the param type of 'this' should determine
        the method's definition class.

        :param name:
        :param arg_types:
        :param lf:
        :return:
        """
        method_id, method_ptr, method_t = self._find_method(name, arg_types, lf)
        def_this_t = method_t.param_types[0].base
        if isinstance(def_this_t, GenericClassType):
            def_this_t = def_this_t.base
        if def_this_t != self:
            raise errs.TplEnvironmentError(f"Cannot resolve local method {name}{arg_types[1:]}. ", lf)
        return method_id, method_ptr, method_t

    def strong_convertible(self, left_tar_type):
        if isinstance(left_tar_type, Generic):
            return self.strong_convertible(left_tar_type.max_t)
        if isinstance(left_tar_type, ClassType):
            real_t = left_tar_type
        elif isinstance(left_tar_type, Generic):
            real_t = left_tar_type.max_t
        elif isinstance(left_tar_type, GenericClassType):
            real_t = left_tar_type.base
        else:
            return super().strong_convertible(left_tar_type)

        for t in self.mro:
            if t == real_t:
                return True
        else:
            return super().strong_convertible(left_tar_type)

    def normal_convertible(self, left_tar_type):
        if self.strong_convertible(left_tar_type):
            return True
        elif isinstance(left_tar_type, GenericClassType):
            if self.strong_convertible(left_tar_type.base) or self.normal_convertible(left_tar_type.base):
                return True
        return super().normal_convertible(left_tar_type)

    def superclass_of(self, child_t: Type):
        if isinstance(child_t, ClassType):
            real_t = child_t
        elif isinstance(child_t, Generic):
            real_t = child_t.max_t
        elif isinstance(child_t, GenericClassType):
            real_t = child_t.base
        else:
            return False
        for t in real_t.mro:
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
        return f"Gen{self.base}<{self.generics}>"


class GenericClassType(GenericType):
    def __init__(self, base: ClassType, generic: dict):
        super().__init__(base, generic)

    def type_name(self):
        return self.base.type_name()

    def strong_convertible(self, left_tar_type):
        # print("000", self)
        # print("112", left_tar_type)
        # print(self.base.super_generics_map)
        if isinstance(left_tar_type, GenericClassType):
            if self.base.strong_convertible(left_tar_type.base):
                # if len(self.generics) == len(left_tar_type.generics):
                for key in left_tar_type.generics:
                    if key in self.generics:  # same class
                        if self.generics[key].strong_convertible(left_tar_type.generics[key]):
                            continue
                    actual_tem_name = self.base.get_actual_template_name(key)
                    if actual_tem_name is not None:
                        if self.generics[actual_tem_name].strong_convertible(left_tar_type.generics[key]):
                            continue
                    return False
                return True
        return False

    def normal_convertible(self, left_tar_type):
        if self.strong_convertible(left_tar_type):
            return True
        if isinstance(left_tar_type, ClassType):
            if self.base.strong_convertible(left_tar_type) or self.base.normal_convertible(left_tar_type):
                return True
        if isinstance(left_tar_type, Generic):
            if self.base.strong_convertible(left_tar_type.max_t) or self.base.normal_convertible(left_tar_type.max_t):
                return True
        return False


class Generic(Type):
    def __init__(self, name: str, max_t: ClassType, class_name: str):
        super().__init__(util.PTR_LEN)

        # print(name, class_name)
        self._name = name
        self.max_t = max_t
        self.class_name = class_name  # class full name

    def strong_convertible(self, left_tar_type):
        return self.max_t.strong_convertible(left_tar_type)

    def simple_name(self):
        return self._name

    def type_name(self):
        return self.max_t.type_name()

    def full_name(self):
        return Generic.generic_name(self.class_name, self._name)

    @staticmethod
    def extract_class_name(full_name: str):
        return full_name[:full_name.rfind("#")]

    @staticmethod
    def simple_gen_name(full_name: str):
        return full_name[full_name.rfind("#") + 1:]

    @staticmethod
    def generic_name(class_name: str, simple_name: str):
        return class_name + "#" + simple_name

    def __eq__(self, other):
        return isinstance(other, Generic) and self._name == other._name and self.class_name == other.class_name

    def __str__(self):
        return f"{self._name}: {self.max_t}"


class ArrayType(Type):
    """
    This class actually represents the array pointer type.
    """
    def __init__(self, ele_type: Type):
        super().__init__(util.PTR_LEN)

        self.ele_type = ele_type

    def strong_convertible(self, left_tar_type):
        if left_tar_type == TYPE_VOID_PTR:
            return True
        elif isinstance(left_tar_type, ArrayType):
            return self.ele_type.strong_convertible(left_tar_type.ele_type)
        # elif isinstance(self.ele_type, PointerType) and isinstance(self.ele_type.base, Generic):
        #     if isinstance(left_tar_type, ArrayType) and isinstance(left_tar_type.ele_type, PointerType):
        #         if isinstance(left_tar_type.ele_type.base, Generic):
        #             if self.ele_type.base.max_t == left_tar_type.ele_type.base.max_t:
        #                 return True
        #         else:
        #             if self.ele_type.base.max_t == left_tar_type.ele_type.base:
        #                 return True
        return super().strong_convertible(left_tar_type)

    def type_name(self):
        return self.ele_type.type_name() + "[]"

    def __str__(self):
        return f"{self.ele_type}[]"

    def __hash__(self):
        return hash(self.ele_type) + 1

    def __eq__(self, other):
        return isinstance(other, ArrayType) and self.ele_type == other.ele_type


def is_object_ptr(t: Type) -> bool:
    return isinstance(t, PointerType) and isinstance(t.base, (ClassType, GenericClassType))


def replace_generics_if(t: Type, caller_class_t, lfp) -> Type:
    if isinstance(caller_class_t, GenericClassType):
        if is_generic(t):
            return replace_generic_with_real(t, caller_class_t.generics, lfp)
        if is_generic_type(t):
            return replace_callee_generic_class(t, caller_class_t, lfp)
    return t


def is_generic(t: Type) -> bool:
    if isinstance(t, PointerType):
        return is_generic(t.base)
    elif isinstance(t, ArrayType):
        return is_generic(t.ele_type)
    return isinstance(t, Generic)


def replace_generic_with_real(t: Type, real_generics: dict, lfp) -> Type:
    if isinstance(t, PointerType):
        return PointerType(replace_generic_with_real(t.base, real_generics, lfp))
    elif isinstance(t, ArrayType):
        return ArrayType(replace_generic_with_real(t.ele_type, real_generics, lfp))
    elif isinstance(t, Generic):
        # print(t.simple_name(), real_generics)
        if real_generics is not None and t.full_name() in real_generics:
            return real_generics[t.full_name()]
        else:
            # situations in, e.g,
            # lst: *List = new List<Integer>();
            # lst.append(new Integer(42));
            # lst.get(0);
            util.print_warning("Unchecked call.", lfp)
            return t.max_t
    else:
        raise errs.TplCompileError("Unexpected error. ", lfp)


def is_generic_type(t: Type) -> bool:
    if isinstance(t, PointerType):
        return is_generic_type(t.base)
    elif isinstance(t, ArrayType):
        return is_generic_type(t.ele_type)
    return isinstance(t, GenericClassType)


def replace_callee_generic_class(t: Type, caller_class_t: GenericClassType, lfp) -> Type:
    if isinstance(t, PointerType):
        return PointerType(replace_callee_generic_class(t.base, caller_class_t, lfp))
    elif isinstance(t, ArrayType):
        return ArrayType(replace_callee_generic_class(t.ele_type, caller_class_t, lfp))
    elif isinstance(t, GenericClassType):
        new_generics = {}
        for key in t.generics:
            value = t.generics[key]
            if is_generic(value):
                replaced = replace_generic_with_real(value, caller_class_t.generics, lfp)
            else:
                replaced = value
            new_generics[key] = replaced

        return GenericClassType(t.base, new_generics)
    else:
        raise errs.TplCompileError("Unexpected error. ", lfp)


def index_in_generic_list(name: str, generics: list) -> int:
    for i in range(len(generics)):
        if name == generics[i].simple_name():
            return i
    return -1


def dict_find_key(d: dict, value):
    for key in d:
        if d[key] == value:
            return key
    return None


def function_poly_name(simple_name: str, params_t: list, method: bool) -> str:
    res = []
    begin = 1 if method else 0
    for i in range(begin, len(params_t)):
        res.append(params_t[i].type_name())
    return simple_name + "(" + ",".join(res) + ")"


def type_eq_no_generic(t1: Type, t2: Type) -> bool:
    if t1 == t2:
        return True

    def get_pointer_base_no_generic(ptr_t):
        if isinstance(ptr_t, PointerType):
            if isinstance(ptr_t.base, ClassType):
                return ptr_t.base
            elif isinstance(ptr_t.base, GenericClassType):
                return ptr_t.base.base
            elif isinstance(ptr_t.base, Generic):
                return ptr_t.base.max_t
        return None

    t1_base = get_pointer_base_no_generic(t1)
    t2_base = get_pointer_base_no_generic(t2)
    if t1_base is None or t2_base is None:
        return False
    return t1_base == t2_base


def params_eq(ft1: FuncType, ft2: FuncType) -> bool:
    if len(ft1.param_types) == len(ft2.param_types):
        for i in range(len(ft1.param_types)):
            if not type_eq_no_generic(ft1.param_types[i], ft2.param_types[i]):
                return False
        return True
    return False


def params_eq_methods(ft1: MethodType, ft2: MethodType) -> bool:
    if len(ft1.param_types) == len(ft2.param_types):
        for i in range(1, len(ft1.param_types)):
            if not type_eq_no_generic(ft1.param_types[i], ft2.param_types[i]):
                return False
        return True
    return False


def func_eq_params(ft: FuncType, param_types: list) -> bool:
    if len(ft.param_types) == len(param_types):
        for i in range(len(param_types)):
            if not type_eq_no_generic(ft.param_types[i], param_types[i]):
                return False
        return True
    return False


def func_convertible_params(ft: FuncType, param_types: list) -> bool:
    if len(ft.param_types) == len(param_types):
        for i in range(len(param_types)):
            if not param_types[i].strong_convertible(ft.param_types[i]):
                return False
        return True
    return False


def method_convertible_params(ft: MethodType, param_types: list) -> bool:
    # print(ft.param_types)
    # print(param_types)
    if len(ft.param_types) == len(param_types):
        for i in range(1, len(param_types)):
            if not param_types[i].strong_convertible(ft.param_types[i]):
                return False
        return True
    return False


def get_class_type(t) -> ClassType:
    if isinstance(t, ClassType):
        return t
    if isinstance(t, GenericClassType):
        return t.base
    if isinstance(t, Generic):
        return t.max_t
    raise errs.TplCompileError("Not a class type.")


def type_distance(left_type, right_real_type):
    """
    Precondition: right_real_type.strong_convertible(left_type)

    :param left_type:
    :param right_real_type:
    :return:
    """
    if isinstance(left_type, PointerType) and isinstance(right_real_type, PointerType):
        if left_type == TYPE_VOID_PTR:  # param: *void
            return 0
        if right_real_type == TYPE_VOID_PTR:  # NULL
            return 0
        left = get_class_type(left_type.base)
        right = get_class_type(right_real_type.base)
        for i in range(len(right.mro)):
            if left == right.mro[i]:
                # print(left, right.mro, i)
                return i

    return 0


def find_closet_func(poly: util.NaiveDict, arg_types: [Type], name: str, is_method: bool,
                     get_type_func, lf) -> (FuncType, object):
    """
    Returns the closet method.

    The closet means the minimum sum of distance.

    :param poly:
    :param arg_types:
    :param name: the simple name of function
    :param is_method:
    :param get_type_func: a function that extract the function type from a unit in poly dict
    :param lf:
    :return: anything that gets from the poly dict.
        usually (method_key_type, (method_id, method_ptr, method_type)) for method,
        (fn_type, (fn_type, fn_ptr)) for function
    """
    param_begin = 1 if is_method else 0
    matched = {}
    for i in range(len(poly)):
        # fn_t = poly.keys[i]
        tup = poly.values[i]
        fn_t: CallableType = get_type_func(poly, i)
        if len(arg_types) == len(fn_t.param_types):
            sum_dt = 0
            match = True
            for j in range(param_begin, len(arg_types)):
                arg = arg_types[j]
                param = fn_t.param_types[j]
                # print(arg, "=====", param, lf)
                # if isinstance(arg, PointerType) and isinstance(arg.base, Generic):
                #     print("zsda")
                if arg.convertible_to(param, lf, weak=False):
                    # print(arg, param, lf, type_distance(param, arg))
                    sum_dt += type_distance(param, arg)
                else:
                    match = False
                    break
            if match:
                if sum_dt in matched:
                    raise errs.TplCompileError(
                        f"Ambiguous call: {function_poly_name(name, arg_types, is_method)}. ", lf)
                matched[sum_dt] = (fn_t, tup)
    min_dt = 65536
    min_tup = None
    for dt in matched:
        if dt < min_dt:
            min_dt = dt
            min_tup = matched[dt]
    if min_tup is None:
        raise errs.TplCompileError(f"Cannot resolve call: {function_poly_name(name, arg_types, is_method)}. ", lf)
    return min_tup


# def find_correspond_tem_name()


TYPE_INT = PrimitiveType("int", util.INT_LEN)
TYPE_FLOAT = PrimitiveType("float", util.FLOAT_LEN)
TYPE_CHAR = PrimitiveType("char", util.CHAR_LEN)
TYPE_BYTE = PrimitiveType("byte", 1)
TYPE_VOID = PrimitiveType("void", 0)

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
    "heap_array": (12, NativeFuncType([TYPE_INT, ArrayType(TYPE_INT)], TYPE_VOID_PTR)),
    "nat_cos": (13, NativeFuncType([TYPE_FLOAT], TYPE_FLOAT)),
    "nat_log": (14, NativeFuncType([TYPE_FLOAT], TYPE_FLOAT)),
    "print_byte": (15, NativeFuncType([TYPE_BYTE], TYPE_VOID)),
    "println_byte": (16, NativeFuncType([TYPE_BYTE], TYPE_VOID)),
    "mem_segment": (17, NativeFuncType([TYPE_VOID_PTR], TYPE_INT)),
    "mem_copy": (18, NativeFuncType([TYPE_VOID_PTR, TYPE_INT, TYPE_VOID_PTR, TYPE_INT, TYPE_INT], TYPE_VOID)),
    "exit": (19, NativeFuncType([TYPE_INT], TYPE_VOID))
}
