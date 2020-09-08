import compilers.errors as errs
import compilers.tokens_lib as tl
import compilers.types as typ


class VarEntry:
    def __init__(self, type_: typ.Type, addr: int, const=False):
        self.type = type_
        self.addr = addr
        self.const = const


class FunctionEntry(VarEntry):
    def __init__(self, type_: typ.Type, addr: int, const=True, named=False):
        super().__init__(type_, addr, const)

        self.named = named  # whether this function entry is defined by keyword 'fn'


class Environment:
    def __init__(self, outer):
        self.outer: Environment = outer

        self.vars: dict[str: VarEntry] = {}

    def define_var(self, name: str, type_: typ.Type, lf: tl.LineFile):
        if self._inner_get(name) is not None:
            raise errs.TplEnvironmentError("Name '{}' already defined. ".format(name), lf)
        entry = VarEntry(type_, -1, False)
        self.vars[name] = entry

    def define_const(self, name: str, type_: typ.Type, lf: tl.LineFile):
        if self._inner_get(name) is not None:
            raise errs.TplEnvironmentError("Name '{}' already defined. ".format(name), lf)
        entry = VarEntry(type_, -1, True)
        self.vars[name] = entry

    def define_var_set(self, name: str, type_: typ.Type, addr: int, lf: tl.LineFile):
        if self._inner_get(name) is not None:
            raise errs.TplEnvironmentError("Name '{}' already defined. ".format(name), lf)
        entry = VarEntry(type_, addr, False)
        self.vars[name] = entry

    def define_const_set(self, name: str, type_: typ.Type, addr: int, lf: tl.LineFile):
        if self._inner_get(name) is not None:
            raise errs.TplEnvironmentError("Name '{}' already defined. ".format(name), lf)
        entry = VarEntry(type_, addr, True)
        self.vars[name] = entry

    def define_function(self, name: str, func_type: typ.CallableType, fn_ptr: int, lf: tl.LineFile):
        if self._inner_get(name) is not None:
            raise errs.TplEnvironmentError("Name '{}' already defined. ".format(name), lf)
        entry = FunctionEntry(func_type, fn_ptr, const=True, named=True)
        self.vars[name] = entry

    def set(self, name, addr, lf):
        entry = self._inner_get(name)
        if entry is None:
            raise errs.TplEnvironmentError("Name '{}' is not defined in this scope. ".format(name), lf)
        entry.addr = addr

    def get_type(self, name, lf) -> typ.Type:
        entry = self._inner_get(name)
        if entry is None:
            raise errs.TplEnvironmentError("Name '{}' is not defined in this scope. ".format(name), lf)
        return entry.type

    def get(self, name, lf) -> int:
        entry = self._inner_get(name)
        if entry is None:
            raise errs.TplEnvironmentError("Name '{}' is not defined in this scope. ".format(name), lf)
        return entry.addr

    def get_struct(self, name, lf):
        pass

    def is_named_function(self, name: str, lf) -> bool:
        entry = self._inner_get(name)
        if entry is None:
            raise errs.TplEnvironmentError("Name '{}' is not defined in this scope. ".format(name), lf)
        if isinstance(entry, FunctionEntry):
            return entry.named
        return False

    def _inner_get(self, name) -> VarEntry:
        if name in self.vars:
            return self.vars[name]
        elif self.outer:
            return self.outer._inner_get(name)
        else:
            return None

    def is_global(self):
        return self.outer is None

    def validate_rtype(self, actual_rtype: typ.Type, lf: tl.LineFile):
        raise errs.TplEnvironmentError("Return outside function. ", lf)


class SubAbstractEnvironment(Environment):
    def __init__(self, outer):
        super().__init__(outer)

    def validate_rtype(self, actual_rtype: typ.Type, lf: tl.LineFile):
        self.outer.validate_rtype(actual_rtype, lf)


class GlobalEnvironment(Environment):
    def __init__(self):
        super().__init__(None)


class FunctionEnvironment(Environment):
    def __init__(self, outer, name: str, rtype: typ.Type):
        super().__init__(outer)

        self.name = name
        self.rtype = rtype

    def validate_rtype(self, actual_rtype: typ.Type, lf: tl.LineFile):
        if not actual_rtype.convert_able(self.rtype):
            raise errs.TplCompileError("Function '{}' has declared return type '{}', got actual return type '{}'. "
                                       .format(self.name, self.rtype, actual_rtype), lf)


class BlockEnvironment(SubAbstractEnvironment):
    def __init__(self, outer):
        super().__init__(outer)
