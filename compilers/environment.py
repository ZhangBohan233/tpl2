import compilers.errors as errs
import compilers.tokens_lib as tl
import compilers.types as typ


class VarEntry:
    def __init__(self, type_: typ.Type, addr: int, const: bool = False):
        self.type = type_
        self.addr = addr
        self.const = const

    def __str__(self):
        pre = "Const" if self.const else "Var"
        return "{}Entry {} @{}".format(pre, self.type, self.addr)

    def __repr__(self):
        return self.__str__()


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

    def is_const(self, name: str, lf) -> bool:
        entry = self._inner_get(name)
        if entry is None:
            raise errs.TplEnvironmentError("Name '{}' is not defined in this scope. ".format(name), lf)
        return entry.const

    def get_type(self, name, lf) -> typ.Type:
        if name in typ.PRIMITIVE_TYPES:
            return typ.PRIMITIVE_TYPES[name]
        entry = self._inner_get(name)
        if entry is None:
            raise errs.TplEnvironmentError("Name '{}' is not defined in this scope. ".format(name), lf)
        return entry.type

    def get(self, name, lf) -> int:
        entry = self._inner_get(name)
        if entry is None:
            raise errs.TplEnvironmentError("Name '{}' is not defined in this scope. ".format(name), lf)
        return entry.addr

    def is_type(self, name, lf) -> bool:
        if name in typ.PRIMITIVE_TYPES:
            return True
        entry = self._inner_get(name)
        if entry is None:
            raise errs.TplEnvironmentError("Name '{}' is not defined in this scope. ".format(name), lf)
        return isinstance(entry.type, typ.StructType)

    def is_named_function(self, name: str, lf) -> bool:
        entry = self._inner_get(name)
        if entry is None:
            raise errs.TplEnvironmentError("Name '{}' is not defined in this scope. ".format(name), lf)
        if isinstance(entry, FunctionEntry):
            return entry.named
        return False

    def has_name(self, name) -> bool:
        return self._inner_get(name) is not None

    def _inner_get(self, name) -> VarEntry:
        if name in self.vars:
            return self.vars[name]
        elif self.outer:
            return self.outer._inner_get(name)
        else:
            return None

    @classmethod
    def is_global(cls):
        return False

    def set_exports(self, exports, lf):
        pass  # do nothing

    def vars_subset(self, names: dict, lf) -> dict:
        """
        :param names: dict of {real name in scope: export name}
        :param lf:
        :return:
        """
        sub = {}
        for name, export_name in names.items():
            entry = self._inner_get(name)
            if entry is None:
                raise errs.TplEnvironmentError("Name '{}' is not defined in this scope. ".format(name), lf)
            sub[export_name] = entry
        return sub

    def import_vars(self, module_exports: dict, lf):
        for name, ve in module_exports.items():
            if self._inner_get(name) is None:
                self.vars[name] = ve
            else:
                raise errs.TplEnvironmentError("Name '{}' already defined. ".format(name), lf)

    def validate_rtype(self, actual_rtype: typ.Type, lf: tl.LineFile):
        raise errs.TplEnvironmentError("Return outside function. ", lf)

    def break_label(self) -> str:
        raise NotImplementedError()

    def continue_label(self) -> str:
        raise NotImplementedError()

    def fallthrough(self):
        raise errs.TplEnvironmentError("Fallthrough outside switch-case")


class SubAbstractEnvironment(Environment):
    def __init__(self, outer):
        super().__init__(outer)

    def validate_rtype(self, actual_rtype: typ.Type, lf: tl.LineFile):
        self.outer.validate_rtype(actual_rtype, lf)

    def break_label(self) -> str:
        return self.outer.break_label()

    def continue_label(self) -> str:
        return self.outer.continue_label()

    def fallthrough(self):
        return self.outer.fallthrough()


class MainAbstractEnvironment(Environment):
    def __init__(self, outer):
        super().__init__(outer)

    def break_label(self) -> str:
        raise errs.TplEnvironmentError()

    def continue_label(self) -> str:
        raise errs.TplEnvironmentError()


class GlobalEnvironment(MainAbstractEnvironment):
    def __init__(self):
        super().__init__(None)

    @classmethod
    def is_global(cls):
        return True


class FunctionEnvironment(MainAbstractEnvironment):
    def __init__(self, outer, name: str, rtype: typ.Type):
        super().__init__(outer)

        self.name = name
        self.rtype = rtype

    def validate_rtype(self, actual_rtype: typ.Type, lf: tl.LineFile):
        if not actual_rtype.convertible_to(self.rtype, lf):
            raise errs.TplCompileError("Function '{}' has declared return type '{}', got actual return type '{}'. "
                                       .format(self.name, self.rtype, actual_rtype), lf)


class ModuleEnvironment(MainAbstractEnvironment):
    def __init__(self):
        super().__init__(None)

        self.exports = None

    def set_exports(self, exports: dict, lf):
        if self.exports is None:
            self.exports = exports
        else:
            raise errs.TplEnvironmentError("Multiple exports in one module. ", lf)


class StructEnvironment(MainAbstractEnvironment):
    def __init__(self, outer):
        super().__init__(outer)

        self.templates = set()

    def add_template(self, name: str):
        self.templates.add(name)


class BlockEnvironment(SubAbstractEnvironment):
    def __init__(self, outer):
        super().__init__(outer)


class CaseEnvironment(SubAbstractEnvironment):
    def __init__(self, outer, fallthrough_label: str = None):
        super().__init__(outer)

        self.fallthrough_label = fallthrough_label

    def fallthrough(self) -> str:
        if self.fallthrough_label is None:
            raise errs.TplEnvironmentError("Default case or case expression cannot have 'fallthrough'. ")
        return self.fallthrough_label


class LoopEnvironment(SubAbstractEnvironment):
    def __init__(self, continue_label: str, break_label: str, outer):
        super().__init__(outer)

        self._continue_label = continue_label
        self._break_label = break_label

    def break_label(self) -> str:
        return self._break_label

    def continue_label(self) -> str:
        return self._continue_label
