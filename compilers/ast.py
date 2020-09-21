from abc import ABC

import compilers.tokens_lib as tl
import compilers.environment as en
import compilers.tpa_producer as tp
import compilers.util as util
import compilers.errors as errs
import compilers.types as typ

BIN_ARITH = 1
BIN_LOGICAL = 2
BIN_BITWISE = 3
BIN_LAZY = 4

UNA_ARITH = 1
UNA_LOGICAL = 2

# VAR_USELESS = 0
VAR_VAR = 1
VAR_CONST = 2

use_compile_to = False


def set_optimize_level(opt_level: int):
    if opt_level >= 1:
        global use_compile_to
        use_compile_to = True


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
        """
        Compile this node, returns the evaluated address if this node is an 'Expression', otherwise return None

        :param env:
        :param tpa:
        :return:
        """
        raise NotImplementedError()

    def definition_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        """
        Returns the type when this node is used for representing a type.

        Two typical use of this method is:
        Right side of ':' when defining variable, e.g. 'x: int';
        Return type of function, e.g. 'fn main() int'

        :param env:
        :param manager:
        :return:
        """
        raise errs.TplTypeError("Name '" + self.__class__.__name__ + "' is not a type. ", self.lf)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        """
        Returns the type of the evaluation value of this node.

        :param env:
        :param manager:
        :return:
        """
        raise NotImplementedError()

    def return_check(self):
        """
        Returns True iff there is a child of this node is a ReturnStmt.

        :return:
        """
        return False


# Expression returns a thing while Statement returns nothing

class Expression(Node, ABC):
    def __init__(self, lf):
        super().__init__(lf)

    def use_compile_to(self) -> bool:
        return False

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int):
        et = self.evaluated_type(env, tpa.manager)
        res = self.compile(env, tpa)
        if et.memory_length() == util.INT_LEN:
            tpa.assign(dst_addr, res)
        elif et.memory_length() == util.CHAR_LEN:
            tpa.assign_char(dst_addr, res)
        else:
            pass


class FakeNode(Node):
    def __init__(self, lf):
        super().__init__(lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        raise errs.NotCompileAbleError("Fake node does not compile. ", self.lf)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        raise errs.NotCompileAbleError("Fake node does not compile. ", self.lf)


class FakeLiteral(FakeNode):
    def __init__(self, value, lf):
        super().__init__(lf)

        self.value = value

    def __str__(self):
        return str(self.value)


class FakeIntLit(FakeLiteral):
    def __init__(self, value, lf):
        super().__init__(value, lf)


class FakeFloatLit(FakeLiteral):
    def __init__(self, value, lf):
        super().__init__(value, lf)


class FakeCharLit(FakeLiteral):
    def __init__(self, value, lf):
        super().__init__(value, lf)


class FakeStrLit(FakeLiteral):
    def __init__(self, value, lf):
        super().__init__(value, lf)


class Statement(Node, ABC):
    def __init__(self, lf):
        super().__init__(lf)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        raise errs.TplTypeError("Statements do not evaluate a type. ", self.lf)


class Line(Expression):
    def __init__(self, lf, *nodes):
        super().__init__(lf)

        self.parts: [Node] = list(nodes)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        res = 0
        for part in self.parts:
            res = part.compile(env, tpa)
        return res

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        pass

    def return_check(self):
        return any([part.return_check() for part in self.parts])

    def __len__(self):
        return len(self.parts)

    def __getitem__(self, item) -> Node:
        return self.parts[item]

    def __str__(self):
        return ", ".join([str(part) for part in self.parts])

    def __repr__(self):
        return "Line"


class BlockStmt(Statement):
    def __init__(self, lf):
        super().__init__(lf)

        self.lines = []

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        for line in self.lines:
            line.compile(env, tpa)

    def return_check(self):
        return any([line.return_check() for line in self.lines])

    def __len__(self):
        return len(self.lines)

    def __getitem__(self, item) -> Line:
        return self.lines[item]

    def __setitem__(self, key, value):
        self.lines[key] = value

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


class NameNode(Expression):
    def __init__(self, name: str, lf):
        super().__init__(lf)

        self.name = name

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        return env.get(self.name, self.lf)

    def definition_type(self, env: en.Environment, manager: tp.Manager):
        if env.is_type(self.name, self.lf):
            return env.get_type(self.name, self.lf)
        else:
            raise errs.TplCompileError(f"Name '{self.name}' is not a type. ", self.lf)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager):
        return env.get_type(self.name, self.lf)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"NameNode({self.name})"


class LiteralNode(Expression, ABC):
    def __init__(self, lit_pos: int, lf):
        super().__init__(lf)

        self.lit_pos = lit_pos


class IntLiteral(LiteralNode):
    def __init__(self, lit_pos, lf):
        super().__init__(lit_pos, lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        stack_addr = tpa.manager.allocate_stack(util.INT_LEN)
        tpa.load_literal(stack_addr, self.lit_pos)
        return stack_addr

    def use_compile_to(self) -> bool:
        return use_compile_to

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int):
        tpa.load_literal(dst_addr, self.lit_pos)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return typ.TYPE_INT

    def __str__(self):
        return "Int@" + str(self.lit_pos)


class FloatLiteral(LiteralNode):
    def __init__(self, lit_pos, lf):
        super().__init__(lit_pos, lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        pass

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return typ.TYPE_FLOAT

    def __str__(self):
        return "Float@" + str(self.lit_pos)


class CharLiteral(LiteralNode):
    def __init__(self, lit_pos, lf):
        super().__init__(lit_pos, lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        stack_addr = tpa.manager.allocate_stack(util.CHAR_LEN)
        tpa.load_char_literal(stack_addr, self.lit_pos)
        return stack_addr

    def use_compile_to(self) -> bool:
        return use_compile_to

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int):
        tpa.load_char_literal(dst_addr, self.lit_pos)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return typ.TYPE_CHAR

    def __str__(self):
        return "Char@" + str(self.lit_pos)


class StringLiteral(LiteralNode):
    def __init__(self, lit_pos, lf):
        super().__init__(lit_pos, lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        res_ptr = tpa.manager.allocate_stack(util.PTR_LEN)
        tpa.load_literal_ptr(res_ptr, self.lit_pos)

        return res_ptr

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return typ.TYPE_CHAR_ARR

    def __str__(self):
        return "String@" + str(self.lit_pos)


class Buildable:
    def __init__(self, op: str):
        self.op = op

    def fulfilled(self):
        raise NotImplementedError()


class UnaryBuildable(Buildable):
    def __init__(self, op, operator_at_left):
        super().__init__(op)

        self.value: Expression = None
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

        self.left: Expression = None
        self.right: Expression = None

    def fulfilled(self):
        return self.left is not None and self.right is not None

    def __str__(self):
        return "BE({} {} {})".format(self.left, self.op, self.right)


class UnaryExpr(Expression, UnaryBuildable, ABC):
    def __init__(self, op: str, lf, operator_at_left=True):
        Expression.__init__(self, lf)
        UnaryBuildable.__init__(self, op, operator_at_left)


class UnaryStmt(Statement, UnaryBuildable, ABC):
    def __init__(self, op: str, lf, operator_at_left=True):
        Statement.__init__(self, lf)
        UnaryBuildable.__init__(self, op, operator_at_left)


class BinaryExpr(Expression, BinaryBuildable, ABC):
    def __init__(self, op: str, lf):
        Expression.__init__(self, lf)
        BinaryBuildable.__init__(self, op)


class BinaryStmt(Statement, BinaryBuildable, ABC):
    def __init__(self, op: str, lf):
        Statement.__init__(self, lf)
        BinaryBuildable.__init__(self, op)


class UnaryOperator(UnaryExpr):
    def __init__(self, op: str, op_type: int, lf):
        super().__init__(op, lf)

        self.op_type = op_type

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        vt: typ.Type = self.value.evaluated_type(env, tpa.manager)
        value = self.value.compile(env, tpa)
        if self.op_type == UNA_ARITH:
            if isinstance(vt, typ.BasicType):
                if vt.type_name == "int":
                    res_addr = tpa.manager.allocate_stack(vt.length)
                    if self.op == "neg":
                        tpa.unary_arith("negi", value, res_addr)
                    else:
                        raise errs.TplCompileError("Unexpected unary operator '{}'. ".format(self.op), self.lf)
                    return res_addr
        elif self.op_type == UNA_LOGICAL:
            if isinstance(vt, typ.BasicType):
                res_addr = tpa.manager.allocate_stack(vt.length)
                if self.op == "not":
                    if vt.type_name != "int":
                        raise errs.TplCompileError("Operator 'not' must take an int as value. ", self.lf)
                    tpa.unary_arith("not", value, res_addr)
                else:
                    raise errs.TplCompileError("Unexpected unary operator '{}'. ".format(self.op), self.lf)
                return res_addr

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        if self.op_type == UNA_ARITH:
            vt = self.value.evaluated_type(env, manager)
            if isinstance(vt, typ.BasicType):
                return vt
        elif self.op_type == UNA_LOGICAL:
            return typ.TYPE_INT
        raise errs.TplCompileError("Value type is not supported by unary operator. ", self.lf)


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
            if isinstance(lt, typ.BasicType):
                if isinstance(rt, typ.BasicType):
                    if lt.type_name == "int":
                        if rt.type_name == "int":
                            res_addr = tpa.manager.allocate_stack(util.INT_LEN)
                            int_int_to_int(self.op, left_addr, right_addr, res_addr, tpa)
                            return res_addr
        elif self.op_type == BIN_BITWISE:
            pass
        elif self.op_type == BIN_LAZY:
            # x and y: if x then y else 0
            # x or y: if x then 1 else y
            if self.op == "and":
                ife = IfExpr(self.left, self.right, IntLiteral(util.ZERO_POS, self.lf), self.lf)
                if not ife.evaluated_type(env, tpa.manager).convertible_to(typ.TYPE_INT, self.lf):
                    raise errs.TplCompileError("Cannot convert {} to {}. ".format(ife, typ.TYPE_INT), self.lf)
                if ife.use_compile_to():
                    pass
                else:
                    return ife.compile(env, tpa)
            elif self.op == "or":
                ife = IfExpr(self.left, IntLiteral(util.ONE_POS, self.lf), self.right, self.lf)
                if not ife.evaluated_type(env, tpa.manager).convertible_to(typ.TYPE_INT, self.lf):
                    raise errs.TplCompileError("Cannot convert {} to {}. ".format(ife, typ.TYPE_INT), self.lf)
                return ife.compile(env, tpa)
            else:
                raise errs.TplCompileError("Unexpected lazy operator. ", self.lf)

    def use_compile_to(self) -> bool:
        return use_compile_to

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int):
        if self.op_type == BIN_ARITH or self.op_type == BIN_LOGICAL:
            lt = self.left.evaluated_type(env, tpa.manager)
            rt = self.right.evaluated_type(env, tpa.manager)
            left_addr = self.left.compile(env, tpa)
            right_addr = self.right.compile(env, tpa)
            if isinstance(lt, typ.BasicType):
                if isinstance(rt, typ.BasicType):
                    if lt.type_name == "int":
                        if rt.type_name == "int":
                            # res_addr = tpa.manager.allocate_stack(util.INT_LEN)
                            int_int_to_int(self.op, left_addr, right_addr, dst_addr, tpa)
                            return dst_addr
        elif self.op_type == BIN_BITWISE:
            pass
        elif self.op_type == BIN_LAZY:
            # x and y: if x then y else 0
            # x or y: if x then 1 else y
            if self.op == "and":
                ife = IfExpr(self.left, self.right, IntLiteral(util.ZERO_POS, self.lf), self.lf)
            elif self.op == "or":
                ife = IfExpr(self.left, IntLiteral(util.ONE_POS, self.lf), self.right, self.lf)
            else:
                raise errs.TplCompileError("Unexpected lazy operator. ", self.lf)

            if not ife.evaluated_type(env, tpa.manager).convertible_to(typ.TYPE_INT, self.lf):
                raise errs.TplCompileError("Cannot convert {} to {}. ".format(ife, typ.TYPE_INT), self.lf)

            ife.compile_to(env, tpa, dst_addr)
            return dst_addr

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        if self.op_type == BIN_ARITH:
            lt = self.left.evaluated_type(env, manager)
            rt = self.right.evaluated_type(env, manager)
            if isinstance(lt, typ.BasicType):
                if isinstance(rt, typ.BasicType):
                    if lt.type_name == "int":
                        if rt.type_name == "int":
                            return typ.TYPE_INT
        elif self.op_type == BIN_LOGICAL or self.op_type == BIN_BITWISE or self.op_type == BIN_LAZY:
            return typ.TYPE_INT
        raise errs.TplCompileError("Value type is not supported by binary operator. ", self.lf)


class BinaryOperatorAssignment(BinaryExpr, FakeNode):
    def __init__(self, op: str, op_type: int, lf):
        BinaryExpr.__init__(self, op, lf)
        FakeNode.__init__(self, lf)

        self.op_type = op_type


class ReturnStmt(UnaryStmt):
    def __init__(self, lf):
        super().__init__("return", lf)

    @classmethod
    def nullable(cls):
        return True

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        if isinstance(self.value, Nothing):  # 'return;'
            env.validate_rtype(typ.TYPE_VOID, self.lf)
        else:
            rtype = self.value.evaluated_type(env, tpa.manager)
            env.validate_rtype(rtype, self.lf)
            value_addr = self.value.compile(env, tpa)
            if rtype.length == util.INT_LEN:
                tpa.return_value(value_addr)
            elif rtype.length == util.CHAR_LEN:
                tpa.return_char_value(value_addr)
        tpa.return_func()

    def return_check(self):
        return True


class StarExpr(UnaryExpr):
    def __init__(self, lf):
        super().__init__("star", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        val = self.value.compile(env, tpa)
        self_t = self.evaluated_type(env, tpa.manager)
        res_addr = tpa.manager.allocate_stack(self_t.length)
        tpa.value_in_addr_op(val, res_addr)
        return res_addr

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        vt = self.value.evaluated_type(env, manager)
        if isinstance(vt, typ.PointerType):
            return vt.base
        else:
            raise errs.TplCompileError("Cannot unpack non-pointer type. ", self.lf)

    def definition_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        vt = self.value.definition_type(env, manager)
        return typ.PointerType(vt)


class AddrExpr(UnaryExpr):
    def __init__(self, lf):
        super().__init__("addr", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        val = self.value.compile(env, tpa)
        res_addr = tpa.manager.allocate_stack(util.PTR_LEN)
        tpa.take_addr(val, res_addr)
        return res_addr

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        vt = self.value.evaluated_type(env, manager)
        return typ.PointerType(vt)


class NewExpr(UnaryExpr):
    def __init__(self, lf):
        super().__init__("new", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        call_res = tpa.manager.allocate_stack(util.PTR_LEN)
        self.compile_to(env, tpa, call_res)
        return call_res

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int):
        if isinstance(self.value, IndexingExpr):
            return self.compile_heap_arr_init(env, tpa, dst_addr)
        t = self.evaluated_type(env, tpa.manager)
        malloc = NameNode("malloc", self.lf)
        req = RequireStmt(malloc, self.lf)
        req.compile(env, tpa)
        malloc_size = tpa.manager.allocate_stack(util.INT_LEN)
        tpa.assign_i(malloc_size, t.memory_length())
        FunctionCall.call(malloc, [(malloc_size, util.INT_LEN)], env, tpa, dst_addr, self.lf)

    def use_compile_to(self) -> bool:
        return use_compile_to

    def compile_heap_arr_init(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr):
        self.value: IndexingExpr
        args = [self.value.get_atomic_node()] + self.value.flatten_args(env, tpa.manager, True)
        FunctionCall(NameNode("array", self.lf), Line(self.lf, *args), self.lf).compile_to(env, tpa, dst_addr)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        if isinstance(self.value, IndexingExpr):
            return self.value.definition_type(env, manager)
        return typ.PointerType(self.value.definition_type(env, manager))


class DelStmt(UnaryStmt):
    def __init__(self, lf):
        super().__init__("del", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        free = NameNode("free", self.lf)
        req = RequireStmt(free, self.lf)
        req.compile(env, tpa)
        fc = FunctionCall(free, Line(self.lf, self.value), self.value)
        fc.compile(env, tpa)


class AsExpr(BinaryExpr):
    """
    Note that this expression may be used in multiple ways: cast / name changing

    All methods of this class are defined for the use of 'cast'
    """

    def __init__(self, lf):
        super().__init__("as", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        right_t = self.right.definition_type(env, tpa.manager)
        left_t = self.left.evaluated_type(env, tpa.manager)
        left = self.left.compile(env, tpa)
        if left_t == right_t:
            return left
        if right_t == typ.TYPE_INT:
            res_addr = tpa.manager.allocate_stack(util.INT_LEN)
            if left_t == typ.TYPE_CHAR:
                tpa.convert_char_to_int(res_addr, left)
            else:
                raise errs.TplCompileError(f"Cannot cast '{left_t}' to '{right_t}'. ", self.lf)
            return res_addr
        elif right_t == typ.TYPE_CHAR:
            res_addr = tpa.manager.allocate_stack(util.CHAR_LEN)
            if left_t == typ.TYPE_INT:
                tpa.convert_int_to_char(res_addr, left)
            else:
                raise errs.TplCompileError(f"Cannot cast '{left_t}' to '{right_t}'. ", self.lf)
            return res_addr

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return self.right.definition_type(env, manager)


class Dot(BinaryExpr):
    def __init__(self, lf):
        super().__init__(".", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        attr_ptr, attr_t = self.get_attr_ptr_and_type(env, tpa)

        res_ptr = tpa.manager.allocate_stack(attr_t.length)
        tpa.value_in_addr_op(attr_ptr, res_ptr)
        return res_ptr

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        struct_t = self.left.evaluated_type(env, manager)
        if isinstance(struct_t, typ.StructType) and isinstance(self.right, NameNode):
            pos, attr_t = struct_t.members[self.right.name]
            return attr_t
        else:
            raise errs.TplCompileError("Left side of dot must be a struct. ", self.lf)

    def get_attr_ptr_and_type(self, env: en.Environment, tpa: tp.TpaOutput) -> (int, typ.Type):
        left_t = self.left.evaluated_type(env, tpa.manager)
        if isinstance(self.right, NameNode):
            if isinstance(left_t, typ.StructType):
                if isinstance(self.left, StarExpr):
                    dollar = DollarExpr(self.lf)
                    dollar.left = self.left.value
                    dollar.right = self.right
                    return dollar.get_attr_ptr_and_type(env, tpa)
                else:
                    struct_addr = self.left.compile(env, tpa)
                    pos, t = left_t.members[self.right.name]
                    res_ptr = tpa.manager.allocate_stack(t.length)
                    tpa.take_addr(struct_addr + pos, res_ptr)
                    return res_ptr, t

        raise errs.TplCompileError("Left side of dot must be a struct. ", self.lf)


class DollarExpr(BinaryExpr):
    """
    This operator is logically equivalent to (Unpack and get attribute).

    For example, s$x is logically equivalent to (*s).x, but due to the implementation, (*s).x would evaluate to
    incorrect result.
    """

    def __init__(self, lf):
        super().__init__("$", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        left_t = self.left.evaluated_type(env, tpa.manager)
        if isinstance(left_t, typ.PointerType) and isinstance(left_t.base, typ.StructType):
            attr_ptr, attr_t = self.get_attr_ptr_and_type(env, tpa)

            res_ptr = tpa.manager.allocate_stack(attr_t.length)
            tpa.value_in_addr_op(attr_ptr, res_ptr)
            return res_ptr
        elif isinstance(left_t, typ.ArrayType) and isinstance(self.right, NameNode):
            return self.array_attributes(env, tpa)

        raise errs.TplCompileError("Left side of dollar must be a pointer to struct or an array. ", self.lf)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        left_t = self.left.evaluated_type(env, manager)
        if isinstance(left_t, typ.PointerType):
            struct_t = left_t.base
            if isinstance(struct_t, typ.StructType) and isinstance(self.right, NameNode):
                pos, attr_t = struct_t.members[self.right.name]
                return attr_t
        elif isinstance(left_t, typ.ArrayType) and isinstance(self.right, NameNode):
            return array_attribute_types(self.right.name, self.lf)

        raise errs.TplCompileError("Left side of dollar must be a pointer to struct or an array. ", self.lf)

    def get_attr_ptr_and_type(self, env: en.Environment, tpa: tp.TpaOutput) -> (int, typ.Type):
        left_t = self.left.evaluated_type(env, tpa.manager)
        if isinstance(self.right, NameNode):
            if isinstance(left_t, typ.PointerType):
                struct_t = left_t.base
                if isinstance(struct_t, typ.StructType):
                    struct_addr = self.left.compile(env, tpa)
                    pos, t = struct_t.members[self.right.name]
                    real_attr_ptr = tpa.manager.allocate_stack(t.length)
                    if t.length == util.INT_LEN:
                        tpa.assign(real_attr_ptr, struct_addr)
                        tpa.binary_arith_i("addi", real_attr_ptr, pos, real_attr_ptr)
                    else:
                        raise errs.TplCompileError("Unsupported length.", self.lf)
                    return real_attr_ptr, t

        raise errs.TplCompileError("Left side of dollar must be a pointer to struct. ", self.lf)

    def array_attributes(self, env: en.Environment, tpa: tp.TpaOutput):
        res_addr = tpa.manager.allocate_stack(util.INT_LEN)
        arr_ptr = self.left.compile(env, tpa)
        tpa.value_in_addr_op(arr_ptr, res_addr)  # since first value in array is the length
        return res_addr


class Assignment(BinaryExpr):
    def __init__(self, lf):
        super().__init__("=", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        right_t = self.right.evaluated_type(env, tpa.manager)
        if isinstance(self.left, NameNode):
            if env.is_const(self.left.name, self.lf):
                raise errs.TplEnvironmentError("Cannot assign constant '{}'. ".format(self.left.name), self.lf)
            left_t = self.left.evaluated_type(env, tpa.manager)
            right_t.check_convertibility(left_t, self.lf)
            left_addr = self.left.compile(env, tpa)
        elif isinstance(self.left, Declaration):
            left_t = self.left.right.definition_type(env, tpa.manager)
            right_t.check_convertibility(left_t, self.lf)
            left_addr = self.left.compile(env, tpa)
        elif isinstance(self.left, StarExpr):
            right_t.check_convertibility(self.left.evaluated_type(env, tpa.manager), self.lf)
            return self.ptr_assign(self.left, env, tpa)
        elif isinstance(self.left, Dot) or isinstance(self.left, DollarExpr):
            right_t.check_convertibility(self.left.evaluated_type(env, tpa.manager), self.lf)
            return self.struct_attr_assign(self.left, env, tpa)
        elif isinstance(self.left, IndexingExpr):
            right_t.check_convertibility(self.left.evaluated_type(env, tpa.manager), self.lf)
            return self.array_index_assign(self.left, self.right, env, tpa, self.lf)
        else:
            raise errs.TplCompileError("Cannot assign to a '{}'.".format(self.left.__class__.__name__), self.lf)

        if self.right.use_compile_to():
            self.right.compile_to(env, tpa, left_addr)
        else:
            right_addr = self.right.compile(env, tpa)
            tpa.assign(left_addr, right_addr)
        return left_addr

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return self.right.evaluated_type(env, manager)

    def struct_attr_assign(self, dot, env: en.Environment, tpa: tp.TpaOutput):
        attr_ptr, attr_t = dot.get_attr_ptr_and_type(env, tpa)
        res_addr = self.right.compile(env, tpa)
        tpa.ptr_assign(res_addr, attr_ptr)
        return res_addr

    @staticmethod
    def array_index_assign(indexing, right, env: en.Environment, tpa: tp.TpaOutput, lf):
        indexed_t = indexing.evaluated_type(env, tpa.manager)
        right_t = right.evaluated_type(env, tpa.manager)
        if not right_t.convertible_to(indexed_t, lf):
            raise errs.TplCompileError(f"Cannot convert type '{right_t}' to '{indexed_t}'. ", lf)

        indexed_ptr = indexing.get_indexed_addr(env, tpa)
        res_addr = right.compile(env, tpa)
        tpa.ptr_assign(res_addr, indexed_ptr)
        return res_addr

    def ptr_assign(self, left: StarExpr, env: en.Environment, tpa: tp.TpaOutput) -> int:
        right_addr = self.right.compile(env, tpa)
        inner_addr = left.value.compile(env, tpa)
        tpa.ptr_assign(right_addr, inner_addr)
        return right_addr


class Declaration(BinaryStmt):
    def __init__(self, level, lf):
        super().__init__(":", lf)

        self.level = level

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        right_t = self.right.definition_type(env, tpa.manager)
        if isinstance(self.left, NameNode):
            rel_addr = tpa.manager.allocate_stack(right_t.memory_length())
            # print(right_t)
            if self.level == VAR_CONST:
                env.define_const_set(self.left.name, right_t, rel_addr, self.lf)
            elif self.level == VAR_VAR:
                env.define_var_set(self.left.name, right_t, rel_addr, self.lf)
            else:
                raise errs.TplCompileError("Unexpected var level. ", self.lf)
            return rel_addr
        else:
            raise errs.TplCompileError("Right side of declaration must be a name. ", self.lf)

    def __str__(self):
        if self.level == VAR_VAR:
            level = "var"
        elif self.level == VAR_CONST:
            level = "const"
        else:
            raise Exception("Unexpected error. ")

        return "BE({} {}: {})".format(level, self.left, self.right)


class QuickAssignment(BinaryStmt):
    def __init__(self, lf):
        super().__init__(":=", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        t = self.right.evaluated_type(env, tpa.manager)
        if not isinstance(self.left, NameNode):
            raise errs.TplCompileError("Left side of ':=' must be name. ", self.lf)

        res_addr = tpa.manager.allocate_stack(t.memory_length())
        env.define_var_set(self.left.name, t, res_addr, self.lf)

        if self.right.use_compile_to():
            self.right.compile_to(env, tpa, res_addr)
        else:
            right_addr = self.right.compile(env, tpa)
            tpa.assign(res_addr, right_addr)


class RightArrowExpr(BinaryExpr):
    def __init__(self, lf):
        super().__init__("->", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        pass

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        pass

    def definition_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        if isinstance(self.left, FunctionTypeExpr):
            pt = []
            for par in self.left.param_line:
                pt.append(par.definition_type(env, manager))
            rt = self.right.definition_type(env, manager)
            ft = typ.FuncType(pt, rt)
            return ft


class FunctionDef(Expression):
    def __init__(self, name: str, params: Line, rtype: Expression, body: BlockStmt, lf):
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

        func_type = typ.FuncType(param_types, rtype)
        env.define_function(self.name, func_type, fn_ptr, self.lf)

        if self.body is not None:
            # check return
            complete_return = self.body.return_check()
            if not complete_return:
                if not rtype.is_void():
                    raise errs.TplCompileError(f"Function '{self.name}' missing a return statement. ", self.lf)

            # compiling
            body_out.add_function(self.name, self.lf.file_name, fn_ptr)
            push_index = body_out.add_indefinite_push()
            self.body.compile(scope, body_out)

            # ending
            if rtype.is_void():
                body_out.return_func()
            body_out.end_func()

            stack_len = body_out.manager.sp - body_out.manager.blocks[-1]
            body_out.modify_indefinite_push(push_index, stack_len)

        tpa.manager.restore_stack()
        body_out.local_generate()
        tpa.manager.map_function(self.name, self.lf.file_name, body_out.result())

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        rtype = self.rtype.definition_type(env, manager)
        param_types = []
        for i in range(len(self.params.parts)):
            param = self.params.parts[i]
            if isinstance(param, Declaration):
                pt = param.right.definition_type(env, manager)
                param_types.append(pt)

        return typ.FuncType(param_types, rtype)

    def __str__(self):
        return "fn {}({}) {} {}".format(self.name, self.params, self.rtype, self.body)


class FunctionTypeExpr(Expression):
    def __init__(self, param_line: Line, lf):
        super().__init__(lf)

        self.param_line = param_line

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        raise errs.NotCompileAbleError(lf=self.lf)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        pass

    def __str__(self):
        return "fn({})".format(self.param_line)


class FunctionCall(Expression):
    def __init__(self, call_obj: Node, args: Line, lf):
        super().__init__(lf)

        self.call_obj = call_obj
        self.args = args

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        func_type = self.call_obj.evaluated_type(env, tpa.manager)
        if isinstance(func_type, typ.CompileTimeFunctionType):
            dst_addr = tpa.manager.allocate_stack(func_type.rtype.memory_length())
            call_compile_time_function(func_type, self.args, env, tpa, dst_addr)
            return dst_addr

        if not isinstance(func_type, typ.CallableType):
            raise errs.TplCompileError("Node {} not callable. ".format(self.call_obj), self.lf)

        rtn_addr = tpa.manager.allocate_stack(func_type.rtype.length)
        self.compile_to(env, tpa, rtn_addr)
        return rtn_addr

    @staticmethod
    def call(call_obj: Node, evaluated_args: list, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int,
             lf, func_type=None):
        if func_type is None:
            func_type = call_obj.evaluated_type(env, tpa.manager)
        if isinstance(call_obj, NameNode):
            if isinstance(func_type, typ.FuncType):
                fn_ptr = env.get(call_obj.name, lf)
                tpa.call_ptr_function(fn_ptr, evaluated_args, dst_addr, func_type.rtype.length)
            elif isinstance(func_type, typ.NativeFuncType):
                fn_ptr = env.get(call_obj.name, lf)
                tpa.invoke_ptr(fn_ptr, evaluated_args, dst_addr, func_type.rtype.length)
            else:
                raise errs.TplError("Unexpected error. ", lf)

    def use_compile_to(self) -> bool:
        return use_compile_to

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int):
        func_type = self.call_obj.evaluated_type(env, tpa.manager)
        if isinstance(func_type, typ.CompileTimeFunctionType):
            call_compile_time_function(func_type, self.args, env, tpa, dst_addr)
            return

        if not isinstance(func_type, typ.CallableType):
            raise errs.TplCompileError("Node {} not callable. ".format(self.call_obj), self.lf)

        if len(func_type.param_types) != len(self.args):
            raise errs.TplCompileError("Parameter length does not match argument length. ", self.lf)
        evaluated_args = []
        for i in range(len(func_type.param_types)):
            param_t = func_type.param_types[i]
            arg_t: typ.Type = self.args[i].evaluated_type(env, tpa.manager)
            if not arg_t.convertible_to(param_t, self.lf):
                raise errs.TplCompileError("Argument type does not match param type. "
                                           "Expected '{}', got '{}'. ".format(param_t, arg_t), self.lf)
            arg_addr = self.args[i].compile(env, tpa)
            evaluated_args.append((arg_addr, arg_t.length))
        self.call(self.call_obj, evaluated_args, env, tpa, dst_addr, self.lf, func_type)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        func_type = self.call_obj.evaluated_type(env, manager)
        if isinstance(func_type, typ.CompileTimeFunctionType):
            return func_type.rtype
        if not isinstance(func_type, typ.CallableType):
            raise errs.TplCompileError("Node {} not callable. ".format(self.call_obj), self.lf)
        return func_type.rtype

    def __str__(self):
        return "{}({})".format(self.call_obj, self.args)


class Nothing(Expression):
    def __init__(self, lf):
        super().__init__(lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        pass

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        pass

    def __str__(self):
        return "nothing"


class RequireStmt(Statement):
    def __init__(self, body, lf):
        super().__init__(lf)

        self.body = body

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        self.require(self.body, env, tpa)

    @classmethod
    def require(cls, node: Node, env: en.Environment, tpa: tp.TpaOutput):
        if isinstance(node, BlockStmt):
            for line in node.lines:
                cls.require(line, env, tpa)
        elif isinstance(node, Line):
            for part in node.parts:
                cls.require(part, env, tpa)
        elif isinstance(node, NameNode):
            name = node.name
            if name in typ.NATIVE_FUNCTIONS:
                if env.has_name(name):
                    if not isinstance(env.get_type(name, node.lf), typ.NativeFuncType):
                        raise errs.TplCompileError(
                            f"Cannot require name '{name}': name already defined in this scope. ", node.lf)
                else:
                    func_id, func_type = typ.NATIVE_FUNCTIONS[name]
                    fn_ptr = tpa.manager.allocate_stack(util.PTR_LEN)
                    tpa.require_name(name, fn_ptr)
                    env.define_function(name, func_type, fn_ptr, node.lf)
            else:
                raise errs.TplCompileError("Cannot require '" + name + "'. ", node.lf)

    def __str__(self):
        return "require " + str(self.body)


class IfStmt(Statement):
    def __init__(self, condition: Expression, if_branch: BlockStmt, else_branch, lf):
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

    def return_check(self):
        # Note that an 'if' without 'else' does not return this function anyway
        return self.if_branch.return_check() and \
               (self.else_branch.return_check() if self.else_branch is not None else False)

    def __str__(self):
        if self.else_branch:
            return "if {} {} else {}".format(self.condition, self.if_branch, self.else_branch)
        else:
            return "if {} {}".format(self.condition, self.if_branch)


class IfExpr(Expression):
    def __init__(self,
                 condition: Expression,
                 then_expr: Expression,
                 else_expr: Expression,
                 lf):
        super().__init__(lf)

        self.condition = condition
        self.then_expr = then_expr
        self.else_expr = else_expr

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        res_t = self.evaluated_type(env, tpa.manager)
        res_addr = tpa.manager.allocate_stack(res_t.length)
        self.compile_to(env, tpa, res_addr)
        return res_addr

    def use_compile_to(self) -> bool:
        return use_compile_to

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int):
        cond_addr = self.condition.compile(env, tpa)

        else_label = tpa.manager.label_manager.else_label()
        endif_label = tpa.manager.label_manager.endif_label()

        tpa.if_zero_goto(cond_addr, else_label)

        if_env = en.BlockEnvironment(env)
        then_addr = self.then_expr.compile(if_env, tpa)
        tpa.assign(dst_addr, then_addr)

        tpa.write_format("goto", endif_label)
        tpa.write_format("label", else_label)

        else_env = en.BlockEnvironment(env)
        else_addr = self.else_expr.compile(else_env, tpa)
        tpa.assign(dst_addr, else_addr)

        tpa.write_format("label", endif_label)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        then_t = self.then_expr.evaluated_type(env, manager)
        else_t = self.else_expr.evaluated_type(env, manager)
        if not (then_t.strong_convertible(else_t) and else_t.strong_convertible(then_t)):
            if not (then_t.weak_convertible(else_t) and else_t.weak_convertible(then_t)):
                raise errs.TplCompileError("Two branches of if-expression must have compatible type. ", self.lf)
            else:
                print("Warning: converting between '{}' and '{}'. {}".format(then_t, else_t, self.lf))
        return then_t

    def __str__(self):
        return "if {} then {} else {}".format(self.condition, self.then_expr, self.else_expr)


class WhileStmt(Statement):
    def __init__(self, condition: Expression, body: BlockStmt, lf):
        super().__init__(lf)

        self.condition = condition
        self.body = body

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        loop_title_label = tpa.manager.label_manager.loop_title_label()
        end_label = tpa.manager.label_manager.end_loop_label()

        loop_env = en.LoopEnvironment(loop_title_label, end_label, env)

        tpa.write_format("label", loop_title_label)
        cond_addr = self.condition.compile(env, tpa)
        tpa.if_zero_goto(cond_addr, end_label)

        self.body.compile(loop_env, tpa)

        tpa.write_format("goto", loop_title_label)
        tpa.write_format("label", end_label)

    def return_check(self):
        return self.body.return_check()

    def __str__(self):
        return "while {} {}".format(self.condition, self.body)


class ForStmt(Statement):
    def __init__(self, title: BlockStmt, body: BlockStmt, lf):
        super().__init__(lf)

        self.body = body
        if len(title) == 3:
            self.init: Node = title[0]
            self.cond: Expression = title[1]
            self.step: Node = title[2]
        else:
            raise errs.TplCompileError("For loop title must contains 3 parts. ", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        loop_title_label = tpa.manager.label_manager.loop_title_label()
        end_label = tpa.manager.label_manager.end_loop_label()
        continue_label = tpa.manager.label_manager.general_label()

        loop_env = en.LoopEnvironment(continue_label, end_label, env)
        self.init.compile(loop_env, tpa)
        tpa.write_format("label", loop_title_label)
        cond = self.cond.compile(loop_env, tpa)
        tpa.if_zero_goto(cond, end_label)

        self.body.compile(loop_env, tpa)

        tpa.write_format("label", continue_label)
        self.step.compile(loop_env, tpa)
        tpa.write_format("goto", loop_title_label)
        tpa.write_format("label", end_label)

    def return_check(self):
        return self.body.return_check()

    def __str__(self):
        return "for {}; {}; {} {}".format(self.init, self.cond, self.step, self.body)


class BreakStmt(Statement):
    def __init__(self, lf):
        super().__init__(lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        end_label = env.break_label()
        tpa.write_format("goto", end_label)

    def __str__(self):
        return "break"


class ContinueStmt(Statement):
    def __init__(self, lf):
        super().__init__(lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        end_label = env.continue_label()
        tpa.write_format("goto", end_label)

    def __str__(self):
        return "continue"


class ExportStmt(Statement):
    def __init__(self, block: BlockStmt, lf):
        super().__init__(lf)

        self.block = block

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        exported_names = {}  # {real name in scope: export name}
        for line in self.block:
            for part in line:
                if isinstance(part, NameNode):
                    exported_names[part.name] = part.name
                    continue
                elif isinstance(part, AsExpr):
                    if isinstance(part.left, NameNode) and isinstance(part.right, NameNode):
                        exported_names[part.left.name] = part.right.name
                        continue

                raise errs.TplCompileError("Export statements must be name or 'as' expression. ", self.lf)
        exported_entries = env.vars_subset(exported_names, self.lf)
        if isinstance(env, en.ModuleEnvironment):
            env.set_exports(exported_entries, self.lf)
        else:
            raise errs.TplCompileError("Export must directly under a file. ", self.lf)

    def __str__(self):
        return "export {}".format(self.block)


class ImportStmt(Statement):
    def __init__(self, file: str, tree: BlockStmt, lf):
        super().__init__(lf)

        self.file = file
        self.tree = tree

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        module_env = en.ModuleEnvironment()
        self.tree.compile(module_env, tpa)
        if module_env.exports is not None:
            env.import_vars(module_env.exports, self.lf)

    def __str__(self):
        return "import {}: {}".format(self.file, self.tree)


class StructStmt(Statement):
    def __init__(self, name: str, body: BlockStmt, lf):
        super().__init__(lf)

        self.name = name
        self.body = body

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        struct_t = self.definition_type(env, tpa.manager)
        env.define_const(self.name, struct_t, self.lf)

    def definition_type(self, env: en.Environment, manager: tp.Manager) -> typ.StructType:
        pos = 0
        members = {}
        for line in self.body:
            for part in line:
                if isinstance(part, Declaration) and isinstance(part.left, NameNode):
                    right_t = part.right.definition_type(env, manager)
                    members[part.left.name] = (pos, right_t)
                    pos += right_t.length
                else:
                    raise errs.TplSyntaxError("Invalid struct member. ", self.lf)
        return typ.StructType(self.name, self.lf.file_name, members, pos)

    def __str__(self):
        return "struct {} {}".format(self.name, self.body)


class IndexingExpr(Expression):
    def __init__(self, indexing_obj: Node, args: Line, lf):
        super().__init__(lf)

        self.indexing_obj = indexing_obj
        self.args = args

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        if self.is_array_initialization(env):
            return array_creation(self, env, tpa)
        else:
            return self.indexing(env, tpa)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        if self.is_array_initialization(env):
            return self.definition_type(env, manager)
        obj_t = self.indexing_obj.evaluated_type(env, manager)
        if isinstance(obj_t, typ.ArrayType):
            return obj_t.ele_type
        else:
            raise errs.TplCompileError("Only array type supports indexing. ", self.lf)

    def definition_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        base = self.indexing_obj.definition_type(env, manager)
        return typ.ArrayType(base)

    def is_array_initialization(self, env: en.Environment):
        if isinstance(self.indexing_obj, IndexingExpr):
            return self.indexing_obj.is_array_initialization(env)
        elif isinstance(self.indexing_obj, NameNode):
            return env.is_type(self.indexing_obj.name, self.lf)
        else:
            return False

    def indexing(self, env: en.Environment, tpa: tp.TpaOutput) -> int:
        res_addr = tpa.manager.allocate_stack(self.evaluated_type(env, tpa.manager).memory_length())
        indexed_addr = self.get_indexed_addr(env, tpa)

        tpa.value_in_addr_op(indexed_addr, res_addr)
        return res_addr

    def get_indexed_addr(self, env: en.Environment, tpa: tp.TpaOutput) -> int:
        ele_t = self.evaluated_type(env, tpa.manager)
        array_ptr_addr = self.indexing_obj.compile(env, tpa)
        index_addr = self._get_index_node(env, tpa.manager).compile(env, tpa)

        arith_addr = tpa.manager.allocate_stack(util.INT_LEN)
        tpa.assign(arith_addr, index_addr)
        tpa.binary_arith_i("muli", arith_addr, ele_t.memory_length(), arith_addr)
        tpa.binary_arith_i("addi", arith_addr, util.INT_LEN, arith_addr)  # this step skips the space storing array size

        tpa.binary_arith("addi", array_ptr_addr, arith_addr, arith_addr)
        # tpa.to_abs(arith_addr, res_addr)
        return arith_addr

    def flatten_args(self, env, manager, neg_one_ifn=False):
        args = []
        node = self
        while isinstance(node, IndexingExpr):
            if len(node.args) == 0:
                if neg_one_ifn:
                    args.insert(0, IntLiteral(util.NEG_ONE_POS, self.lf))
                else:
                    raise errs.TplCompileError("Array arg must contain exactly one value. ", self.lf)
            else:
                args.insert(0, node._get_index_node(env, manager))
            node = node.indexing_obj
        return args

    def get_atomic_node(self):
        if isinstance(self.indexing_obj, IndexingExpr):
            return self.indexing_obj.get_atomic_node()
        else:
            return self.indexing_obj

    def _get_atom_type(self, env, manager):
        return self.get_atomic_node().evaluated_type(env, manager)

    def _get_index_node(self, env, manager) -> Node:
        if len(self.args) != 1:
            raise errs.TplCompileError("Array initialization or indexing must contain exactly one int element. ",
                                       self.lf)
        arg: Node = self.args[0]
        if arg.evaluated_type(env, manager) != typ.TYPE_INT:
            raise errs.TplCompileError("Array initialization or indexing must contain exactly one int element. ",
                                       self.lf)
        return arg

    def get_index_literal(self, env, manager: tp.Manager):
        node = self._get_index_node(env, manager)
        if not isinstance(node, IntLiteral):
            raise errs.TplCompileError("Array type declaration must be an int literal. ", self.lf)
        return util.bytes_to_int(manager.literal[node.lit_pos: node.lit_pos + util.INT_LEN])

    def __str__(self):
        return f"{self.indexing_obj}[{self.args}]"


class PreIncDecOperator(UnaryExpr):
    def __init__(self, op, lf):
        super().__init__(op, lf, True)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        if isinstance(self.value, PreIncDecOperator) or isinstance(self.value, PostIncDecOperator):
            raise errs.TplCompileError("Expression not assignable. ", self.lf)
        if isinstance(self.value, Dot) or isinstance(self.value, DollarExpr) or isinstance(self.value, IndexingExpr):
            return self.compile_non_suitable(env, tpa)

        vt = self.value.evaluated_type(env, tpa.manager)
        if vt == typ.TYPE_INT:
            op = "addi" if self.op == "++" else "subi"
            v_addr = self.value.compile(env, tpa)
            tpa.binary_arith_i(op, v_addr, 1, v_addr)
            return v_addr
        elif vt == typ.TYPE_FLOAT:
            pass
        else:
            raise errs.TplCompileError(f"Cannot apply '{self.op}' to type '{vt}'. ", self.lf)

    def compile_non_suitable(self, env: en.Environment, tpa: tp.TpaOutput):
        # replace ++expr by expr = expr + 1
        ass = Assignment(self.lf)
        one = IntLiteral(util.ONE_POS, self.lf)
        opn = BinaryOperator("+" if self.op == "++" else "-", BIN_ARITH, self.lf)
        opn.left = self.value
        opn.right = one
        ass.left = self.value
        ass.right = opn
        ass.compile(env, tpa)

        return self.value.compile(env, tpa)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return self.value.evaluated_type(env, manager)

    def __str__(self):
        return f"{self.op}{self.value}"


class PostIncDecOperator(UnaryExpr):
    def __init__(self, op, lf):
        super().__init__(op, lf, False)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        if isinstance(self.value, PreIncDecOperator) or isinstance(self.value, PostIncDecOperator):
            raise errs.TplCompileError("Expression not assignable. ", self.lf)
        if isinstance(self.value, Dot) or isinstance(self.value, DollarExpr) or isinstance(self.value, IndexingExpr):
            return self.compile_attr_op(env, tpa)

        vt = self.value.evaluated_type(env, tpa.manager)
        if vt == typ.TYPE_INT:
            op = "addi" if self.op == "++" else "subi"
            res_addr = tpa.manager.allocate_stack(util.INT_LEN)
            v_addr = self.value.compile(env, tpa)
            tpa.assign(res_addr, v_addr)
            tpa.binary_arith_i(op, v_addr, 1, v_addr)
            return res_addr
        elif vt == typ.TYPE_FLOAT:
            pass
        else:
            raise errs.TplCompileError(f"Cannot apply '{self.op}' to type '{vt}'. ", self.lf)

    def compile_attr_op(self, env: en.Environment, tpa: tp.TpaOutput):
        # replace a.x by a.x = a.x + 1
        v = self.value.compile(env, tpa)

        ass = Assignment(self.lf)
        one = IntLiteral(util.ONE_POS, self.lf)
        opn = BinaryOperator("+" if self.op == "++" else "-", BIN_ARITH, self.lf)
        opn.left = self.value
        opn.right = one
        ass.left = self.value
        ass.right = opn
        ass.compile(env, tpa)

        return v

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return self.value.evaluated_type(env, manager)

    def __str__(self):
        return f"{self.value}{self.op}"


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


def array_creation(node, env: en.Environment, tpa: tp.TpaOutput) -> int:
    res_addr = tpa.manager.allocate_stack(util.PTR_LEN)

    dimensions = []
    while isinstance(node, IndexingExpr):
        if len(node.args) == 0:
            dimensions.insert(0, -1)
        else:
            dimensions.insert(0, node.get_index_literal(env, tpa.manager))
        node = node.indexing_obj

    if dimensions[0] == -1:
        raise errs.TplCompileError("Outermost array must have a declared size. ", node.lf)

    root_t = node.evaluated_type(env, tpa.manager)
    create_array_rec(res_addr, root_t, dimensions, 0, env, tpa)
    return res_addr


def create_array_rec(this_ptr_addr, atom_t: typ.Type, dimensions: list, index_in_dim: int,
                     env: en.Environment, tpa: tp.TpaOutput):
    arr_size = dimensions[index_in_dim]
    if arr_size == -1:
        return
    if index_in_dim == len(dimensions) - 1:
        ele_len = atom_t.memory_length()
    else:
        ele_len = util.PTR_LEN
    arr_addr = tpa.manager.allocate_stack(ele_len * arr_size + util.INT_LEN)
    tpa.assign_i(arr_addr, arr_size)
    tpa.take_addr(arr_addr, this_ptr_addr)

    if index_in_dim == len(dimensions) - 1:
        pass
    else:
        first_ele_addr = arr_addr + util.INT_LEN
        for i in range(arr_size):
            create_array_rec(first_ele_addr + i * util.PTR_LEN, atom_t, dimensions, index_in_dim + 1, env, tpa)


def array_attribute_types(attr_name: str, lf):
    if attr_name == "length":
        return typ.TYPE_INT

    raise errs.TplCompileError(f"Array does not have attribute '{attr_name}'. ", lf)


def validate_arg_count(args: Line, expected_arg_count):
    if len(args) != expected_arg_count:
        raise errs.TplCompileError("Arity mismatch for compile time function. ", args.lf)


def ctf_sizeof(args: Line, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int):
    validate_arg_count(args, 1)
    t = args[0].evaluated_type(env, tpa.manager)
    tpa.assign_i(dst_addr, t.memory_length())


PRINT_FUNCTIONS = {
    typ.TYPE_INT: "print_int",
    typ.TYPE_FLOAT: "print_float",
    typ.TYPE_CHAR: "print_char",
    typ.TYPE_CHAR_ARR: "print_str"
}

PRINTLN_FUNCTIONS = {
    typ.TYPE_INT: "println_int",
    typ.TYPE_FLOAT: "println_float",
    typ.TYPE_CHAR: "println_char",
    typ.TYPE_CHAR_ARR: "println_str"
}


def ctf_cprint(args: Line, env: en.Environment, tpa: tp.TpaOutput):
    validate_arg_count(args, 1)
    arg: Node = args[0]
    et = arg.evaluated_type(env, tpa.manager)
    if et in PRINT_FUNCTIONS:
        name_node = NameNode(PRINT_FUNCTIONS[et], args.lf)
        RequireStmt.require(name_node, env, tpa)
        call = FunctionCall(name_node, args, args.lf)
        return call.compile(env, tpa)
    else:
        raise errs.TplCompileError("Unexpected argument type of 'cprint'. ", args.lf)


def ctf_cprintln(args: Line, env: en.Environment, tpa: tp.TpaOutput):
    validate_arg_count(args, 1)
    arg: Node = args[0]
    et = arg.evaluated_type(env, tpa.manager)
    if et in PRINTLN_FUNCTIONS:
        name_node = NameNode(PRINTLN_FUNCTIONS[et], args.lf)
        RequireStmt.require(name_node, env, tpa)
        call = FunctionCall(name_node, args, args.lf)
        return call.compile(env, tpa)
    else:
        raise errs.TplCompileError("Unexpected argument type of 'cprint'. ", args.lf)


def ctf_array(args: Line, env: en.Environment, tpa: tp.TpaOutput, dst_addr):
    if len(args) < 2:
        raise errs.TplCompileError("Function 'array' requires at least 2 arguments: element type, dimension. ", args.lf)
    dim = [len(args) - 1]
    arr_ptr = tpa.manager.allocate_stack(util.PTR_LEN)
    create_array_rec(arr_ptr, typ.TYPE_INT, dim, 0, env, tpa)
    arith_addr = tpa.manager.allocate_stack(util.INT_LEN)
    argc = len(args)
    for i in range(1, argc):
        arg = args[i]  # reverse dimension array like in 'IndexingExpr'
        arg_t = arg.evaluated_type(env, tpa.manager)
        if arg_t != typ.TYPE_INT:
            raise errs.TplCompileError(f"Expected argument type 'int', got '{arg_t}'. ", arg.lf)
        tpa.binary_arith_i("addi", arr_ptr, i * util.INT_LEN, arith_addr)  # (i - 1) * INT_LEN + INT_LEN
        arg_addr = arg.compile(env, tpa)
        tpa.ptr_assign(arg_addr, arith_addr)

    sizeof_name = NameNode("sizeof", args.lf)
    sizeof_call = FunctionCall(sizeof_name, Line(args.lf, args[0]), args.lf)
    sizeof_res = sizeof_call.compile(env, tpa)

    fn_name = NameNode("heap_array", args.lf)
    req = RequireStmt(fn_name, args.lf)
    req.compile(env, tpa)
    FunctionCall.call(fn_name, [(sizeof_res, util.INT_LEN), (arr_ptr, util.PTR_LEN)],
                      env, tpa, dst_addr, args.lf)


COMPILE_TIME_FUNCTIONS = {
    typ.CompileTimeFunctionType("sizeof", typ.TYPE_INT): ctf_sizeof,
    typ.CompileTimeFunctionType("cprint", typ.TYPE_VOID): ctf_cprint,
    typ.CompileTimeFunctionType("cprintln", typ.TYPE_VOID): ctf_cprintln,
    typ.CompileTimeFunctionType("array", typ.TYPE_VOID_PTR): ctf_array
}


def call_compile_time_function(func_t: typ.CompileTimeFunctionType, arg: Line,
                               env: en.Environment, tpa: tp.TpaOutput, dst_addr: int):
    f = COMPILE_TIME_FUNCTIONS[func_t]
    if f.__code__.co_argcount == 3:
        f(arg, env, tpa)
    else:
        f(arg, env, tpa, dst_addr)
