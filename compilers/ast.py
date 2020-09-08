from abc import ABC

import compilers.tokens_lib as tl
import compilers.environment as en
import compilers.tpa_producer as tp
import compilers.util as util
import compilers.errors as errs

BIN_ARITH = 1
BIN_LOGICAL = 2
BIN_BITWISE = 3
BIN_LAZY = 4

UNA_ARITH = 1
UNA_LOGICAL = 2

# VAR_USELESS = 0
VAR_VAR = 1
VAR_CONST = 2


class SpaceCounter:
    def __init__(self):
        self.count = 0

    def add_space(self):
        self.count += 2

    def remove_space(self):
        self.count -= 2

    def get(self):
        return self.count


SPACES = SpaceCounter()


class Node:
    def __init__(self, lf):
        self.lf: tl.LineFile = lf

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        raise NotImplementedError()

    def definition_type(self, env: en.Environment, manager: tp.Manager) -> en.Type:
        raise errs.TplTypeError("Name '" + self.__class__.__name__ + "' is not a type. ", self.lf)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> en.Type:
        raise NotImplementedError()


class AbstractExpression(Node, ABC):
    def __init__(self, lf):
        super().__init__(lf)


class AbstractStatement(Node, ABC):
    def __init__(self, lf):
        super().__init__(lf)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> en.Type:
        raise errs.TplTypeError("Statements do not evaluate a type. ", self.lf)


class Line(AbstractExpression):
    def __init__(self, lf):
        super().__init__(lf)

        self.parts: [Node] = []

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        res = 0
        for part in self.parts:
            res = part.compile(env, tpa)
        return res

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> en.Type:
        pass

    def __len__(self):
        return len(self.parts)

    def __getitem__(self, item):
        return self.parts[item]

    def __str__(self):
        return ", ".join([str(part) for part in self.parts])

    def __repr__(self):
        return "Line"


class BlockStmt(AbstractStatement):
    def __init__(self, lf):
        super().__init__(lf)

        self.lines = []

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        for line in self.lines:
            line.compile(env, tpa)

    def __str__(self):
        s = "\n" + " " * SPACES.get() + "{"
        SPACES.add_space()
        for line in self.lines:
            s += "\n" + " " * SPACES.get() + str(line)
        SPACES.remove_space()
        s += "\n" + " " * SPACES.get() + "}"
        return s

    def __repr__(self):
        return "BlockStmt"


class NameNode(AbstractExpression):
    def __init__(self, name: str, lf):
        super().__init__(lf)

        self.name = name

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        return env.get(self.name, self.lf)

    def definition_type(self, env: en.Environment, manager: tp.Manager):
        if self.name == "int":
            return en.TYPE_INT
        elif self.name == "float":
            return en.TYPE_FLOAT
        elif self.name == "char":
            return en.TYPE_CHAR
        elif self.name == "void":
            return en.TYPE_VOID
        else:
            return env.get_struct(self.name, self.lf)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager):
        return env.get_type(self.name, self.lf)

    def __str__(self):
        return self.name


class LiteralNode(AbstractExpression, ABC):
    def __init__(self, lf):
        super().__init__(lf)


class IntLiteral(LiteralNode):
    def __init__(self, lit_pos, lf):
        super().__init__(lf)

        self.lit_pos: int = lit_pos

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        stack_addr = tpa.manager.allocate_stack(util.INT_LEN)
        tpa.load_literal(stack_addr, self.lit_pos)
        return stack_addr

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> en.Type:
        return en.TYPE_INT

    def __str__(self):
        return "Int@" + str(self.lit_pos)


class FloatLiteral(LiteralNode):
    def __init__(self, lit_pos, lf):
        super().__init__(lf)

        self.lit_pos: int = lit_pos

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        pass

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> en.Type:
        return en.TYPE_FLOAT

    def __str__(self):
        return "Float@" + str(self.lit_pos)


class CharLiteral(LiteralNode):
    def __init__(self, lit_pos, lf):
        super().__init__(lf)

        self.lit_pos: int = lit_pos

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        pass

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> en.Type:
        return en.TYPE_CHAR

    def __str__(self):
        return "Char@" + str(self.lit_pos)


class StringLiteral(LiteralNode):
    def __init__(self, lf):
        super().__init__(lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        pass


class Buildable:
    def __init__(self, op: str):
        self.op = op

    def fulfilled(self):
        raise NotImplementedError()


class UnaryBuildable(Buildable):
    def __init__(self, op, operator_at_left):
        super().__init__(op)

        self.value: AbstractExpression = None
        self.operator_at_left = operator_at_left

    @classmethod
    def nullable(cls):
        return False

    def fulfilled(self):
        return self.value is not None

    def __str__(self):
        if self.operator_at_left:
            return "UE({} {})".format(self.op, self.value)
        else:
            return "UE({} {})".format(self.value, self.op)


class BinaryBuildable(Buildable):
    def __init__(self, op):
        super().__init__(op)

        self.left: AbstractExpression = None
        self.right: AbstractExpression = None

    def fulfilled(self):
        return self.left is not None and self.right is not None

    def __str__(self):
        return "BE({} {} {})".format(self.left, self.op, self.right)


class UnaryExpr(AbstractExpression, UnaryBuildable, ABC):
    def __init__(self, op: str, lf, operator_at_left=True):
        AbstractExpression.__init__(self, lf)
        UnaryBuildable.__init__(self, op, operator_at_left)


class UnaryStmt(AbstractStatement, UnaryBuildable, ABC):
    def __init__(self, op: str, lf, operator_at_left=True):
        AbstractStatement.__init__(self, lf)
        UnaryBuildable.__init__(self, op, operator_at_left)


class BinaryExpr(AbstractExpression, BinaryBuildable, ABC):
    def __init__(self, op: str, lf):
        AbstractExpression.__init__(self, lf)
        BinaryBuildable.__init__(self, op)


class UnaryOperator(UnaryExpr):
    def __init__(self, op: str, op_type: int, lf):
        super().__init__(op, lf)

        self.op_type = op_type

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        pass

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> en.Type:
        pass


class BinaryOperator(BinaryExpr):
    def __init__(self, op: str, op_type: int, lf):
        super().__init__(op, lf)

        self.op_type = op_type

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        if self.op_type == BIN_ARITH or self.op_type == BIN_LOGICAL:
            lt = self.left.evaluated_type(env, tpa.manager)
            rt = self.right.evaluated_type(env, tpa.manager)
            left_addr = self.left.compile(env, tpa)
            right_addr = self.right.compile(env, tpa)
            if isinstance(lt, en.BasicType):
                if isinstance(rt, en.BasicType):
                    if lt.type_name == "int":
                        if rt.type_name == "int":
                            res_addr = tpa.manager.allocate_stack(util.INT_LEN)
                            int_int_to_int(self.op, left_addr, right_addr, res_addr, tpa)
                            return res_addr
        elif self.op_type == BIN_BITWISE:
            pass
        elif self.op_type == BIN_LAZY:
            pass

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> en.Type:
        if self.op_type == BIN_ARITH:
            lt = self.left.evaluated_type(env, manager)
            rt = self.right.evaluated_type(env, manager)
            if isinstance(lt, en.BasicType):
                if isinstance(rt, en.BasicType):
                    if lt.type_name == "int":
                        if rt.type_name == "int":
                            return en.TYPE_INT
        elif self.op_type == BIN_LOGICAL or self.op_type == BIN_BITWISE or self.op_type == BIN_LAZY:
            return en.TYPE_INT


class BinaryOperatorAssignment(BinaryExpr):
    def __init__(self, op: str, op_type: int, lf):
        super().__init__(op, lf)

        self.op_type = op_type

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        pass


class FakeTernaryOperator(BinaryExpr):
    def __init__(self, op: str, lf):
        super().__init__(op, lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        pass


class ReturnStmt(UnaryStmt):
    def __init__(self, lf):
        super().__init__("return", lf)

    @classmethod
    def nullable(cls):
        return True

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        if isinstance(self.value, Nothing):  # 'return;'
            env.validate_rtype(en.TYPE_VOID, self.lf)
        else:
            rtype = self.value.evaluated_type(env, tpa.manager)
            env.validate_rtype(rtype, self.lf)
            value_addr = self.value.compile(env, tpa)
            tpa.return_value(value_addr)
        tpa.return_func()


class StarExpr(UnaryExpr):
    def __init__(self, lf):
        super().__init__("star", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        pass


class Assignment(BinaryExpr):
    def __init__(self, lf):
        super().__init__("=", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        if isinstance(self.left, NameNode):
            left_addr = self.left.compile(env, tpa)
        elif isinstance(self.left, Declaration):
            left_addr = self.left.compile(env, tpa)
        else:
            raise errs.TplCompileError("Cannot assign to a '{}'.".format(self.__class__.__name__), self.lf)

        right_addr = self.right.compile(env, tpa)
        tpa.assign(left_addr, right_addr)
        return left_addr

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> en.Type:
        pass


class Declaration(BinaryExpr):
    def __init__(self, level, lf):
        super().__init__(":", lf)

        self.level = level

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        typ = self.right.definition_type(env, tpa.manager)
        if isinstance(self.left, NameNode):
            rel_addr = tpa.manager.allocate_stack(typ.length)
            if self.level == VAR_CONST:
                env.define_const_set(self.left.name, typ, rel_addr, self.lf)
            elif self.level == VAR_VAR:
                env.define_var_set(self.left.name, typ, rel_addr, self.lf)
            else:
                raise errs.TplCompileError("", self.lf)
            return rel_addr
        else:
            raise errs.TplCompileError("", self.lf)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> en.Type:
        pass

    def __str__(self):
        if self.level == VAR_VAR:
            level = "var"
        elif self.level == VAR_CONST:
            level = "const"
        else:
            raise Exception("Unexpected error. ")

        return "BE({} {}: {})".format(level, self.left, self.right)


class RightArrowExpr(BinaryExpr):
    def __init__(self, lf):
        super().__init__("->", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        pass

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> en.Type:
        pass

    def definition_type(self, env: en.Environment, manager: tp.Manager) -> en.Type:
        if isinstance(self.left, FunctionTypeExpr):
            pt = []
            for par in self.left.param_line:
                pt.append(par.definition_type(env, manager))
            rt = self.right.definition_type(env, manager)
            ft = en.FuncType(pt, rt)
            return ft


class FunctionDef(AbstractExpression):
    def __init__(self, name: str, params: Line, rtype: AbstractExpression, body: BlockStmt, lf):
        super().__init__(lf)

        self.name = name
        self.params = params
        self.rtype = rtype
        self.body = body

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        rtype = self.rtype.definition_type(env, tpa.manager)
        fn_ptr = tpa.manager.allocate_stack(util.PTR_LEN)

        scope = en.FunctionEnvironment(env, self.name, rtype)
        tpa.manager.push_stack()

        body_out = tp.TpaOutput(tpa.manager)

        param_types = []
        for i in range(len(self.params.parts)):
            param = self.params.parts[i]
            if isinstance(param, Declaration):
                pt = param.right.definition_type(env, tpa.manager)
                param_types.append(pt)
                param.compile(scope, body_out)

        func_type = en.FuncType(param_types, rtype)
        env.define_function(self.name, func_type, fn_ptr, self.lf)

        if self.body is not None:
            body_out.add_function(self.name, fn_ptr)
            push_index = body_out.add_indefinite_push()
            self.body.compile(scope, body_out)

            if rtype.is_void():
                body_out.return_func()
            body_out.end_func()

            stack_len = body_out.manager.sp - body_out.manager.blocks[-1]
            body_out.modify_indefinite_push(push_index, stack_len)

        tpa.manager.restore_stack()
        body_out.generate()
        tpa.manager.map_function(self.name, body_out.result())

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> en.Type:
        pass

    def __str__(self):
        return "fn {}({}) {} {}".format(self.name, self.params, self.rtype, self.body)


class FunctionTypeExpr(AbstractExpression):
    def __init__(self, param_line: Line, lf):
        super().__init__(lf)

        self.param_line = param_line

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        raise errs.NotCompileAbleError(lf=self.lf)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> en.Type:
        pass

    def __str__(self):
        return "fn({})".format(self.param_line)


class FunctionCall(AbstractExpression):
    def __init__(self, call_obj: Node, args: Line, lf):
        super().__init__(lf)

        self.call_obj = call_obj
        self.args = args

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        func_type = self.call_obj.evaluated_type(env, tpa.manager)
        if not isinstance(func_type, en.CallableType):
            raise errs.TplCompileError("Node {} not callable. ".format(self.call_obj), self.lf)
        if isinstance(func_type, en.FuncType):
            if len(func_type.param_types) != len(self.args):
                raise errs.TplCompileError("Parameter length does not match argument length. ", self.lf)
            evaluated_args = []
            for i in range(len(func_type.param_types)):
                param_t = func_type.param_types[i]
                arg_t: en.Type = self.args[i].evaluated_type(env, tpa.manager)
                if not arg_t.convert_able(param_t):
                    raise errs.TplCompileError("Argument type does not match param type. "
                                               "Expected '{}', got '{}'. ".format(param_t, arg_t), self.lf)
                arg_addr = self.args[i].compile(env, tpa)
                evaluated_args.append((arg_addr, arg_t.length))
            if isinstance(self.call_obj, NameNode):
                rtn_addr = tpa.manager.allocate_stack(func_type.rtype.length)
                if env.is_named_function(self.call_obj.name, self.lf):
                    tpa.call_named_function(self.call_obj.name, evaluated_args, rtn_addr, func_type.rtype.length)
                else:
                    fn_ptr = env.get(self.call_obj.name, self.lf)
                    tpa.call_ptr_function(fn_ptr, evaluated_args, rtn_addr, func_type.rtype.length)
                return rtn_addr

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> en.Type:
        func_type = self.call_obj.evaluated_type(env, manager)
        if not isinstance(func_type, en.CallableType):
            raise errs.TplCompileError("Node {} not callable. ".format(self.call_obj), self.lf)
        if isinstance(func_type, en.FuncType):
            return func_type.rtype

    def __str__(self):
        return "{}({})".format(self.call_obj, self.args)


class Nothing(AbstractExpression):
    def __init__(self, lf):
        super().__init__(lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        pass

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> en.Type:
        pass

    def __str__(self):
        return "nothing"


class RequireStmt(AbstractStatement):
    def __init__(self, body, lf):
        super().__init__(lf)

        self.body = body

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        pass

    def __str__(self):
        return "require " + str(self.body)


class IfStmt(AbstractStatement):
    def __init__(self, condition: AbstractExpression, if_branch: BlockStmt, else_branch, lf):
        super().__init__(lf)

        self.condition = condition
        self.if_branch = if_branch
        self.else_branch = else_branch

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        cond_addr = self.condition.compile(env, tpa)

        else_label = tpa.manager.label_manager.else_label()
        endif_label = tpa.manager.label_manager.endif_label()

        if self.else_branch:
            tpa.if_zero_goto(cond_addr, else_label)
        else:
            tpa.if_zero_goto(cond_addr, endif_label)

        if_env = en.BlockEnvironment(env)
        self.if_branch.compile(if_env, tpa)

        if self.else_branch:
            tpa.write_format("goto", endif_label)
            tpa.write_format("label", else_label)

            else_env = en.BlockEnvironment(env)
            self.else_branch.compile(else_env, tpa)

        tpa.write_format("label", endif_label)

    def __str__(self):
        if self.else_branch:
            return "if {} {} else {}".format(self.condition, self.if_branch, self.else_branch)
        else:
            return "if {} {}".format(self.condition, self.if_branch)


INT_ARITH_TABLE = {
    "+": "addi",
    "-": "subi",
    "*": "muli",
    "/": "divi",
    "%": "modi"
}

INT_LOGIC_TABLE = {
    "==": "eqi",
    "!=": "nei",
    ">": "gti",
    "<": "lti",
    ">=": "gei",
    "<=": "lei"
}


def int_int_to_int(op: str, left_addr: int, right_addr: int, res_addr: int, tpa: tp.TpaOutput):
    if op in INT_ARITH_TABLE:
        op_inst = INT_ARITH_TABLE[op]
    elif op in INT_LOGIC_TABLE:
        op_inst = INT_LOGIC_TABLE[op]
    else:
        raise errs.TplCompileError("No such binary operator '" + op + "'. ")
    tpa.binary_arith(op_inst, left_addr, right_addr, res_addr)
