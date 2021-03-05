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

PUBLIC = 0
PROTECTED = 1
PRIVATE = 2


def set_optimize_level(opt_level: int):
    if opt_level >= 1:
        pass


class IntWrapper:
    def __init__(self, init_value=0):
        self.num = init_value

    def set(self, num):
        self.num = num

    def get(self):
        return self.num


class Counter(IntWrapper):
    def __init__(self, init_value=0):
        super().__init__(init_value)

    def increment(self):
        cur = self.get()
        self.set(cur + 1)
        return cur


class SpaceCounter(Counter):
    def __init__(self):
        super().__init__()

    def add_space(self):
        self.set(self.get() + 2)

    def remove_space(self):
        self.set(self.get() - 2)


SPACES = SpaceCounter()
CLASS_ID = Counter()


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

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int, dst_len: int):
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


class FakeByteLit(FakeLiteral):
    def __init__(self, value, lf):
        super().__init__(value, lf)


class FakeStrLit(FakeLiteral):
    def __init__(self, value, lf):
        super().__init__(value, lf)


class Statement(Node, ABC):
    def __init__(self, lf):
        super().__init__(lf)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        raise errs.TplTypeError(f"Statements {self} do not evaluate a type. ", self.lf)


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

    def __eq__(self, other):
        return type(self) == type(other) and self.parts == other.parts


class BlockStmt(Statement):
    def __init__(self, lf):
        super().__init__(lf)

        self.lines = []

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        for line in self.lines:
            line.compile(env, tpa)

    def return_check(self):
        return any([line.return_check() for line in self.lines])

    def get_first_content(self):
        for line in self.lines:
            for part in line:
                return part
        return None

    def insert_at(self, part_index, lines: [Line]):
        line_index = 0
        for i in range(len(self.lines)):
            for _ in self.lines[i]:
                if part_index == 0:
                    line_index = i
                    break
                else:
                    part_index -= 1
        self.lines = self.lines[:line_index] + lines + self[line_index:]

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
        if env.has_name(self.name):
            if env.is_type(self.name, self.lf):
                return env.get_type(self.name, self.lf)
        else:  # try template
            wc = env.get_working_class()
            if wc is not None:
                prob_name = typ.Generic.generic_name(wc.full_name(), self.name)
                if env.is_type(prob_name, self.lf):
                    return env.get_type(prob_name, self.lf)
        raise errs.TplCompileError(f"Name '{self.name}' is not a type. ", self.lf)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager):
        if env.has_name(self.name):
            return env.get_type(self.name, self.lf)
        else:
            wc = env.get_working_class()
            if wc is not None:
                prob_name = typ.Generic.generic_name(wc.full_name(), self.name)
                if env.is_type(prob_name, self.lf):
                    return env.get_type(prob_name, self.lf)
        raise errs.TplCompileError(f"Name '{self.name}' not defined. ", self.lf)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"NameNode({self.name})"

    def __eq__(self, other):
        return type(self) == type(other) and self.name == other.name


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

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int, dst_len: int):
        tpa.load_literal(dst_addr, self.lit_pos)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return typ.TYPE_INT

    def __str__(self):
        return "Int@" + str(self.lit_pos)


class FloatLiteral(LiteralNode):
    def __init__(self, lit_pos, lf):
        super().__init__(lit_pos, lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        stack_addr = tpa.manager.allocate_stack(util.FLOAT_LEN)
        tpa.load_literal(stack_addr, self.lit_pos)
        return stack_addr

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int, dst_len: int):
        tpa.load_literal(dst_addr, self.lit_pos)

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

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int, dst_len: int):
        tpa.load_char_literal(dst_addr, self.lit_pos)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return typ.TYPE_CHAR

    def __str__(self):
        return "Char@" + str(self.lit_pos)


class ByteLiteral(LiteralNode):
    def __init__(self, lit_pos, lf):
        super().__init__(lit_pos, lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        stack_addr = tpa.manager.allocate_stack(1)
        tpa.load_byte_literal(stack_addr, self.lit_pos)
        return stack_addr

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int, dst_len: int):
        tpa.load_byte_literal(dst_addr, self.lit_pos)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return typ.TYPE_BYTE

    def __str__(self):
        return "Char@" + str(self.lit_pos)


class CharArrayLiteral(LiteralNode):
    def __init__(self, lit_pos, lf):
        super().__init__(lit_pos, lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        res_ptr = tpa.manager.allocate_stack(util.PTR_LEN)
        self.compile_to(env, tpa, res_ptr, util.PTR_LEN)
        return res_ptr

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int, dst_len: int):
        tpa.load_literal_ptr(dst_addr, self.lit_pos)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return typ.TYPE_CHAR_ARR

    def __str__(self):
        return "CharArray@" + str(self.lit_pos)


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

    def __eq__(self, other):
        return type(self) == type(other) and self.op == other.op and self.value == other.value


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
            if isinstance(vt, typ.PrimitiveType):
                if vt == typ.TYPE_INT:
                    res_addr = tpa.manager.allocate_stack(util.INT_LEN)
                    if self.op == "neg":
                        tpa.unary_arith("negi", value, res_addr)
                    else:
                        raise errs.TplCompileError("Unexpected unary operator '{}'. ".format(self.op), self.lf)
                    return res_addr
                elif vt == typ.TYPE_FLOAT:
                    res_addr = tpa.manager.allocate_stack(util.FLOAT_LEN)
                    if self.op == "neg":
                        tpa.unary_arith("negf", value, res_addr)
                    else:
                        raise errs.TplCompileError("Unexpected unary operator '{}'. ".format(self.op), self.lf)
                    return res_addr
        elif self.op_type == UNA_LOGICAL:
            if isinstance(vt, typ.PrimitiveType):
                res_addr = tpa.manager.allocate_stack(vt.length)
                if self.op == "not":
                    if vt.t_name != "int":
                        raise errs.TplCompileError("Operator 'not' must take an int as value. ", self.lf)
                    tpa.unary_arith("not", value, res_addr)
                else:
                    raise errs.TplCompileError("Unexpected unary operator '{}'. ".format(self.op), self.lf)
                return res_addr
        raise errs.TplCompileError(f"Unsupported unary operator '{self.op}'")

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        if self.op_type == UNA_ARITH:
            vt = self.value.evaluated_type(env, manager)
            if isinstance(vt, typ.PrimitiveType):
                return vt
        elif self.op_type == UNA_LOGICAL:
            return typ.TYPE_INT
        raise errs.TplCompileError("Value type is not supported by unary operator. ", self.lf)


class BinaryOperator(BinaryExpr):
    def __init__(self, op: str, op_type: int, lf):
        super().__init__(op, lf)

        self.op_type = op_type

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        res_t = self.evaluated_type(env, tpa.manager)
        res_addr = tpa.manager.allocate_stack(res_t.memory_length())
        self.compile_to(env, tpa, res_addr, res_t.memory_length())
        return res_addr

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int, dst_len: int):
        def convert_addr_to_int(src_t, src_addr):
            if src_t == typ.TYPE_CHAR:
                res_addr = tpa.manager.allocate_stack(util.INT_LEN)
                tpa.convert_char_to_int(res_addr, src_addr)
                return res_addr
            elif src_t == typ.TYPE_BYTE:
                res_addr = tpa.manager.allocate_stack(util.INT_LEN)
                tpa.convert_byte_to_int(res_addr, src_addr)
                return res_addr
            return src_addr

        def convert_addr_to_float(src_t, src_addr):
            if src_t == typ.TYPE_FLOAT:
                return src_addr
            src_addr = convert_addr_to_int(src_t, src_addr)
            res_addr = tpa.manager.allocate_stack(util.FLOAT_LEN)
            tpa.convert_int_to_float(res_addr, src_addr)
            return res_addr

        if self.op_type == BIN_ARITH or self.op_type == BIN_LOGICAL:
            lt = self.left.evaluated_type(env, tpa.manager)
            rt = self.right.evaluated_type(env, tpa.manager)
            left_addr = self.left.compile(env, tpa)
            right_addr = self.right.compile(env, tpa)
            if isinstance(lt, typ.PrimitiveType):
                if isinstance(rt, typ.PrimitiveType):
                    if lt.int_like():
                        if rt.int_like():
                            left_convert_addr = convert_addr_to_int(lt, left_addr)
                            right_convert_addr = convert_addr_to_int(rt, right_addr)
                            int_int_to_int(self.op, left_convert_addr, right_convert_addr, dst_addr, tpa)
                            return
                        elif rt == typ.TYPE_FLOAT:
                            left_convert_addr = convert_addr_to_float(lt, left_addr)
                            float_float_to_float(self.op, left_convert_addr, right_addr, dst_addr, tpa)
                            return
                    elif lt == typ.TYPE_FLOAT:
                        right_convert_addr = convert_addr_to_float(rt, right_addr)
                        float_float_to_float(self.op, left_addr, right_convert_addr, dst_addr, tpa)
                        return
            elif isinstance(lt, typ.PointerType) and isinstance(rt, typ.PointerType):
                if self.op == "==" or self.op == "!=":
                    int_int_to_int(self.op, left_addr, right_addr, dst_addr, tpa)
                    return
        elif self.op_type == BIN_BITWISE:
            lt = self.left.evaluated_type(env, tpa.manager)
            rt = self.right.evaluated_type(env, tpa.manager)
            left_addr = self.left.compile(env, tpa)
            right_addr = self.right.compile(env, tpa)
            if lt == typ.TYPE_INT and rt == typ.TYPE_INT:
                int_int_to_int(self.op, left_addr, right_addr, dst_addr, tpa)
                return
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

            ife.compile_to(env, tpa, dst_addr, dst_len)
            return

        raise errs.TplCompileError(f"Unsupported binary operation {self.op} between "
                                   f"{self.left.evaluated_type(env, tpa.manager)} and "
                                   f"{self.right.evaluated_type(env, tpa.manager)}. ", self.lf)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        if self.op_type == BIN_ARITH:
            lt = self.left.evaluated_type(env, manager)
            rt = self.right.evaluated_type(env, manager)
            if isinstance(lt, typ.PrimitiveType):
                if isinstance(rt, typ.PrimitiveType):
                    if lt.int_like():
                        if rt.int_like():
                            return typ.TYPE_INT
                        elif rt == typ.TYPE_FLOAT:
                            return typ.TYPE_FLOAT
                    elif lt == typ.TYPE_FLOAT:
                        return typ.TYPE_FLOAT
        elif self.op_type == BIN_LOGICAL or self.op_type == BIN_BITWISE or self.op_type == BIN_LAZY:
            return typ.TYPE_INT
        raise errs.TplCompileError(f"Unsupported binary operation {self.op} between "
                                   f"{self.left.evaluated_type(env, manager)} and "
                                   f"{self.right.evaluated_type(env, manager)}. ", self.lf)


class BinaryOperatorAssignment(BinaryExpr, FakeNode):
    def __init__(self, op: str, op_type: int, lf):
        BinaryExpr.__init__(self, op, lf)
        FakeNode.__init__(self, lf)

        self.op_type = op_type


class InstanceOfExpr(BinaryExpr):
    def __init__(self, lf):
        super().__init__("instanceof", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        dst_addr = tpa.manager.allocate_stack(util.INT_LEN)
        self.compile_to(env, tpa, dst_addr, util.INT_LEN)
        return dst_addr

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int, dst_len: int):
        class_node = DotExpr(self.lf)
        class_node.left = self.left
        class_node.right = NameNode("__class__", self.lf)

        right_t = self.right.evaluated_type(env, tpa.manager)
        if not isinstance(right_t, typ.ClassType):
            raise errs.TplCompileError("Right side of 'instanceof' must be class. ")
        right_ptr_addr = self.right.compile(env, tpa)
        ins_class_ptr_addr = class_node.compile(env, tpa)
        tpa.subclass_of(right_ptr_addr, ins_class_ptr_addr, dst_addr)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return typ.TYPE_INT


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
            elif rtype.length == 1:
                tpa.return_byte_value(value_addr)
            else:
                raise errs.TplCompileError("Unexpected value length. ", self.lf)
        tpa.return_func()

    def return_check(self):
        return True


class StarExpr(UnaryExpr):
    def __init__(self, lf):
        super().__init__("star", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        val = self.value.compile(env, tpa)
        self_t = self.evaluated_type(env, tpa.manager)
        res_addr = tpa.manager.allocate_stack(self_t.memory_length())
        tpa.value_in_addr_op(val, self_t.memory_length(), res_addr, self_t.memory_length())
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
        self.compile_to(env, tpa, call_res, util.PTR_LEN)
        return call_res

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int, dst_len: int):
        if isinstance(self.value, IndexingExpr):
            return self.compile_heap_arr_init(env, tpa, dst_addr, dst_len)
        t = self.evaluated_type(env, tpa.manager)
        malloc_t = self._malloc_type(env, tpa.manager)

        malloc = NameNode("malloc", self.lf)
        req = RequireStmt(malloc, self.lf)
        req.compile(env, tpa)
        malloc_size = tpa.manager.allocate_stack(util.INT_LEN)
        tpa.assign_i(malloc_size, malloc_t.memory_length())
        FunctionCall.call(malloc, [(malloc_size, util.INT_LEN)], env, tpa, dst_addr, self.lf)

        if (isinstance(self.value, FunctionCall) and
                isinstance(t, typ.PointerType)):
            if isinstance(t.base, typ.ClassType):
                self.compile_class_init(t.base, env, tpa, dst_addr)
                return
            elif isinstance(t.base, typ.GenericClassType):
                self.compile_generic_class_init(t.base, env, tpa, dst_addr)
                return

        raise errs.TplCompileError("Cannot initial class without call. ", self.lf)

    def compile_generic_class_init(self, gen_t: typ.GenericClassType, env: en.Environment,
                                   tpa: tp.TpaOutput, inst_ptr_addr):
        # print(gen_t)
        self.compile_class_init(gen_t.base, env, tpa, inst_ptr_addr)

    def compile_class_init(self, class_t: typ.ClassType, env: en.Environment, tpa: tp.TpaOutput, inst_ptr_addr):
        self.value: FunctionCall

        if class_t.abstract:
            raise errs.TplCompileError(f"Abstract class '{class_t.name_with_path}' is not initialisable. ", self.lf)
        tpa.i_ptr_assign(class_t.class_ptr, util.PTR_LEN, inst_ptr_addr)  # assign __class__

        const_args = self.value.arg_types(env, tpa.manager)
        const_args.insert(0, None)  # insert a positional arg of 'this'

        constructor_id, constructor_ptr, constructor_t = \
            class_t.find_local_method("__new__", const_args, self.lf)

        ea = self.value.evaluate_args(constructor_t, env, tpa, True)
        ea.insert(0, (inst_ptr_addr, util.PTR_LEN))
        FunctionCall.call_name(util.name_with_path(
            typ.function_poly_name("__new__", constructor_t.param_types, True), class_t.file_path, class_t),
            ea,
            tpa,
            0,
            self.lf,
            constructor_t)

    def compile_heap_arr_init(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr, dst_len: int):
        self.value: IndexingExpr
        args = [self.value.get_atomic_node()] + self.value.flatten_args(env, tpa.manager, True)
        FunctionCall(NameNode("array", self.lf), Line(self.lf, *args), self.lf).compile_to(env, tpa, dst_addr, dst_len)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        if isinstance(self.value, IndexingExpr):
            return self.value.definition_type(env, manager)
        if isinstance(self.value, FunctionCall):
            return typ.PointerType(self.value.call_obj.definition_type(env, manager))
        return typ.PointerType(self.value.definition_type(env, manager))

    def _malloc_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        if isinstance(self.value, IndexingExpr):
            return self.value.definition_type(env, manager)
        if isinstance(self.value, FunctionCall):
            return self.value.call_obj.definition_type(env, manager)
        return self.value.definition_type(env, manager)


class DelStmt(UnaryStmt):
    def __init__(self, lf):
        super().__init__("del", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        free = NameNode("free", self.lf)
        req = RequireStmt(free, self.lf)
        req.compile(env, tpa)

        val_t = self.value.evaluated_type(env, tpa.manager)
        self.instance_del(val_t, env, tpa)

        fc = FunctionCall(free, Line(self.lf, self.value), self.value)
        fc.compile(env, tpa)

    def instance_del(self, val_t, env, tpa):
        if isinstance(val_t, typ.ClassType):
            self.compile_class_del(val_t, env, tpa)
        elif isinstance(val_t, typ.GenericClassType):
            self.compile_class_del(val_t.base, env, tpa)
        elif isinstance(val_t, typ.Generic):
            self.instance_del(val_t.max_t, env, tpa)

    def compile_class_del(self, class_t: typ.ClassType, env: en.Environment, tpa: tp.TpaOutput):
        inst_ptr_addr = self.value.compile(env, tpa)
        destructor_id, destructor_ptr, destructor_t = class_t.methods["__del__"]
        ea = [(inst_ptr_addr, util.PTR_LEN)]
        tpa.call_method(inst_ptr_addr, destructor_id, ea, 0, 0, 0)


class YieldStmt(UnaryStmt):
    def __init__(self, lf):
        super().__init__("yield", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        pass


class AsExpr(BinaryExpr):
    """
    Note that this expression may be used in multiple ways: cast / name changing

    All methods of this class are defined for the use of 'cast'
    """

    def __init__(self, lf):
        super().__init__("as", lf)

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int, dst_len: int):
        right_t = self.right.definition_type(env, tpa.manager)
        left_t = self.left.evaluated_type(env, tpa.manager)
        left = self.left.compile(env, tpa)
        if left_t == right_t:
            tpa.assign(dst_addr, left)
            return
        if right_t == typ.TYPE_INT:
            if left_t == typ.TYPE_CHAR:
                tpa.convert_char_to_int(dst_addr, left)
                return
            elif left_t == typ.TYPE_BYTE:
                tpa.convert_byte_to_int(dst_addr, left)
                return
            elif left_t == typ.TYPE_FLOAT:
                tpa.convert_float_to_int(dst_addr, left)
                return
            elif left_t == typ.TYPE_VOID_PTR:
                tpa.assign(dst_addr, left)
                return
        elif right_t == typ.TYPE_CHAR:
            if left_t == typ.TYPE_INT:
                tpa.convert_int_to_char(dst_addr, left)
                return
        elif right_t == typ.TYPE_BYTE:
            if left_t == typ.TYPE_INT:
                tpa.convert_int_to_byte(dst_addr, left)
                return
        elif right_t == typ.TYPE_FLOAT:
            if left_t == typ.TYPE_INT:
                tpa.convert_int_to_float(dst_addr, left)
                return
        elif typ.is_object_ptr(left_t) and typ.is_object_ptr(right_t):
            tpa.assign(dst_addr, left)
            return
        elif right_t == typ.TYPE_VOID_PTR:
            if left_t == typ.TYPE_INT or isinstance(left_t, typ.PointerType):
                tpa.assign(dst_addr, left)
                return
            elif isinstance(left_t, typ.ArrayType):
                tpa.assign(dst_addr, left)
                return
        elif isinstance(right_t, typ.ArrayType):
            if left_t == typ.TYPE_VOID_PTR:
                tpa.assign(dst_addr, left)
                return

        raise errs.TplCompileError(f"Cannot cast '{left_t}' to '{right_t}'. ", self.lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        dst_t = self.evaluated_type(env, tpa.manager)
        dst_addr = tpa.manager.allocate_stack(dst_t.memory_length())
        self.compile_to(env, tpa, dst_addr, dst_t.memory_length())
        return dst_addr

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return self.right.definition_type(env, manager)


class DollarExpr(BinaryExpr):
    def __init__(self, lf):
        super().__init__("$", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        attr_ptr, attr_t = self.get_attr_ptr_and_type(env, tpa)

        res_ptr = tpa.manager.allocate_stack(attr_t.memory_length())
        tpa.value_in_addr_op(attr_ptr, attr_t.memory_length(), res_ptr, attr_t.memory_length())
        return res_ptr

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        struct_t = self.left.evaluated_type(env, manager)

        raise errs.TplCompileError("Left side of dollar must be a struct, got " + type(struct_t).__name__ + ". ",
                                   self.lf)

    def get_attr_ptr_and_type(self, env: en.Environment, tpa: tp.TpaOutput) -> (int, typ.Type):
        left_t = self.left.evaluated_type(env, tpa.manager)
        if isinstance(self.right, NameNode):
            pass

        raise errs.TplCompileError("Left side of dollar must be a struct, got " + type(left_t).__name__ + ". ",
                                   self.lf)


class DotExpr(BinaryExpr):
    """
    This operator is logically equivalent to (Unpack and get attribute).

    For example, s.x is logically equivalent to (*s)$x, but due to the implementation, (*s)$x would evaluate to
    incorrect result.
    """

    def __init__(self, lf):
        super().__init__(".", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        return DotExpr.compile_dot(self.left, self.right, env, tpa, self.lf)

    @staticmethod
    def compile_super(right_node, env: en.Environment, tpa: tp.TpaOutput, lf):
        method_env = env
        while not isinstance(method_env, en.MethodEnvironment):
            if method_env is None:
                raise errs.TplCompileError("'super' outside method. ", lf)
            method_env = method_env.outer
        # method_env: en.MethodEnvironment
        cur_method_cls_t: typ.ClassType = method_env.defined_class
        if len(cur_method_cls_t.mro) == 1:
            raise errs.TplCompileError("Class 'Object' has no superclass. ", lf)

        this_ptr = env.get("this", lf)

        if isinstance(right_node, NameNode):
            pass
        elif isinstance(right_node, FunctionCall):
            return DotExpr.compile_fixed_method_call(
                right_node, typ.PointerType(cur_method_cls_t.mro[1]), this_ptr, env, tpa, lf)

        raise errs.TplCompileError("Super must follow a name or a call. ", lf)

    @staticmethod
    def compile_method_call(right_node, class_ptr_t, ins_ptr_addr, env: en.Environment, tpa: tp.TpaOutput,
                            lf, class_offset=0):
        """
        Compiles a method call, with mro resolved at runtime.
        """

        def inner_call(ct: typ.ClassType, right, generics):
            right: FunctionCall
            name = right.get_name()
            arg_types = right_node.arg_types(env, tpa.manager)
            arg_types.insert(0, None)  # insert a positional arg of 'this'
            method_id, method_p, t = ct.find_method(name, arg_types, lf)
            DotExpr.check_permission(t.defined_class, t.permission, env, lf)
            t = t.copy()
            for i in range(len(t.param_types)):
                pt = t.param_types[i]
                if typ.is_generic(pt):
                    t.param_types[i] = typ.replace_generic_with_real(pt, generics)
            res_ptr = tpa.manager.allocate_stack(t.rtype.memory_length())
            ea = right.evaluate_args(t, env, tpa, is_method=True)
            ea.insert(0, (ins_ptr_addr, util.PTR_LEN))
            tpa.call_method(ins_ptr_addr, method_id, ea, res_ptr, t.rtype.memory_length(), class_offset)
            return res_ptr

        # print(class_offset)
        if isinstance(class_ptr_t, typ.PointerType):
            class_t = class_ptr_t.base
            if isinstance(class_t, typ.ClassType):
                return inner_call(class_t, right_node, None)
            elif isinstance(class_t, typ.GenericClassType):
                return inner_call(class_t.base, right_node, class_t.generics)
        raise errs.TplCompileError("Cannot make method call. ", lf)

    @staticmethod
    def compile_fixed_method_call(right_node, class_ptr_t, ins_ptr_addr, env: en.Environment,
                                  tpa: tp.TpaOutput, lf):
        """
        Compiles a method call, with mro resolved at compile time.

        Note that if ins_ptr_addr == -1, it is a static method call.
        For example, Object.hash(obj)
        """
        is_method = ins_ptr_addr >= 0
        if isinstance(class_ptr_t, typ.PointerType):
            class_t = class_ptr_t.base
            if isinstance(class_t, typ.ClassType):
                name = right_node.get_name()
                arg_types = right_node.arg_types(env, tpa.manager)
                if is_method:
                    arg_types.insert(0, None)  # insert a positional arg of 'this'
                method_id, method_p, t = class_t.find_method(name, arg_types, lf)
                if t.abstract:
                    raise errs.TplCompileError(f"Abstract method '{name}' cannot be called. ", lf)
                DotExpr.check_permission(t.defined_class, t.permission, env, lf)
                full_name = util.name_with_path(
                    typ.function_poly_name(name, arg_types, method=True),  # do not modify 'method=True'
                    t.defined_class.file_path, t.defined_class)
                res_ptr = tpa.manager.allocate_stack(t.rtype.memory_length())
                ea = right_node.evaluate_args(t, env, tpa, is_method=is_method)
                if is_method:
                    ea.insert(0, (ins_ptr_addr, util.PTR_LEN))
                FunctionCall.call_name(full_name, ea, tpa, res_ptr, lf, t)
                return res_ptr
        raise errs.TplCompileError("Cannot make method call. ", lf)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return DotExpr.dot_right_t(self.left, self.right, env, manager, self.lf)

    @staticmethod
    def array_attributes(left_node, env: en.Environment, tpa: tp.TpaOutput, name: str, lf):
        res_addr = tpa.manager.allocate_stack(util.INT_LEN)
        arr_ptr = left_node.compile(env, tpa)
        if name == "length":
            tpa.value_in_addr_op(arr_ptr, util.INT_LEN, res_addr, util.INT_LEN)
            # since first value in array is the length
            return res_addr

        raise errs.TplCompileError(f"Array type does not have attribute '{name}'. ", lf)

    # helper functions for dot
    @staticmethod
    def compile_dot(left_node: Expression, right_node: Node, env: en.Environment, tpa: tp.TpaOutput, lf):
        if isinstance(left_node, SuperExpr):
            return DotExpr.compile_super(right_node, env, tpa, lf)
        left_t = left_node.evaluated_type(env, tpa.manager)
        if isinstance(left_t, typ.PointerType):
            if isinstance(right_node, FunctionCall):
                return DotExpr.compile_method_call(right_node, left_t, left_node.compile(env, tpa), env, tpa, lf)
            attr_ptr, attr_t, const = DotExpr.get_dot_attr_and_type(left_node, right_node, env, tpa, lf)

            res_ptr = tpa.manager.allocate_stack(attr_t.memory_length())
            tpa.value_in_addr_op(attr_ptr, attr_t.memory_length(), res_ptr, attr_t.memory_length())
            return res_ptr
        elif isinstance(left_t, typ.ArrayType) and isinstance(right_node, NameNode):
            return DotExpr.array_attributes(left_node, env, tpa, right_node.name, lf)
        elif isinstance(left_t, typ.ClassType):
            if isinstance(right_node, FunctionCall):  # call via Class.method(obj, ...)
                return DotExpr.compile_fixed_method_call(right_node,
                                                         typ.PointerType(left_t), -1, env, tpa, lf)

        raise errs.TplCompileError("Left side of dot must be a pointer to struct or an array. ", lf)

    @staticmethod
    def check_permission(class_t: typ.ClassType, perm, env, lf):
        if perm != PUBLIC:
            wc = env.get_working_class()
            if wc is None:
                raise errs.TplCompileError("Cannot access private or protected field outside class. ",
                                           lf)
            if perm == PRIVATE:
                if wc != class_t:
                    raise errs.TplCompileError("Cannot access private field outside its defining class. ",
                                               lf)
            elif perm == PROTECTED:
                if not class_t.superclass_of(wc):
                    raise errs.TplCompileError("Cannot access protected field outside its defining class or its "
                                               "child class. ",
                                               lf)

    @staticmethod
    def get_dot_attr_and_type(left_node: Expression, right_node: Node, env: en.Environment, tpa: tp.TpaOutput,
                              lf) -> (int, typ.Type, bool):
        left_t = left_node.evaluated_type(env, tpa.manager)
        if isinstance(right_node, NameNode):
            if isinstance(left_t, typ.PointerType):
                struct_t = left_t.base
                if isinstance(struct_t, typ.ClassType):
                    struct_addr = left_node.compile(env, tpa)
                    pos, t, class_t, const, perm = struct_t.find_field(right_node.name, lf)
                    DotExpr.check_permission(class_t, perm, env, lf)

                    real_attr_ptr = tpa.manager.allocate_stack(t.length)
                    if t.length == util.INT_LEN:
                        tpa.assign(real_attr_ptr, struct_addr)
                        tpa.i_binary_arith("addi", real_attr_ptr, pos, real_attr_ptr)
                    else:
                        raise errs.TplCompileError("Unsupported length. ", lf)
                    return real_attr_ptr, t, const
                elif isinstance(struct_t, typ.GenericClassType):
                    struct_addr = left_node.compile(env, tpa)
                    pos, t, class_t, const, perm = struct_t.base.find_field(right_node.name, lf)
                    if isinstance(t, str):
                        t = struct_t.generics[t]
                    DotExpr.check_permission(class_t, perm, env, lf)
                    real_attr_ptr = tpa.manager.allocate_stack(t.length)
                    if t.length == util.INT_LEN:
                        tpa.assign(real_attr_ptr, struct_addr)
                        tpa.i_binary_arith("addi", real_attr_ptr, pos, real_attr_ptr)
                    else:
                        raise errs.TplCompileError("Unsupported length.", lf)
                    return real_attr_ptr, t, const

        raise errs.TplCompileError("Left side of dot must be a pointer to class. ", lf)

    @staticmethod
    def dot_type(left_node: Expression, right_node: Node, env: en.Environment, manager: tp.Manager, lf):
        return DotExpr.dot_right_t(left_node, right_node, env, manager, lf)

    @staticmethod
    def dot_right_t(left_node: Expression, right_node, env, manager, lf):
        left_t = left_node.evaluated_type(env, manager)
        if isinstance(left_t, typ.PointerType):
            struct_t = left_t.base
            if isinstance(right_node, NameNode):
                if isinstance(struct_t, typ.ClassType):
                    pos, attr_t, class_t, const, perm = struct_t.find_field(right_node.name, lf)
                    return attr_t
                elif isinstance(struct_t, typ.GenericClassType):
                    pos, attr_t, class_t, const, perm = struct_t.base.find_field(right_node.name, lf)
                    if typ.is_generic(attr_t):
                        return typ.replace_generic_with_real(attr_t, struct_t.generics)
                    return attr_t
            elif isinstance(right_node, FunctionCall):
                arg_types = right_node.arg_types(env, manager)
                arg_types.insert(0, None)
                if isinstance(struct_t, typ.ClassType):
                    name = right_node.get_name()
                    pos, ptr, t = struct_t.find_method(name, arg_types, lf)
                    return t.rtype
                elif isinstance(struct_t, typ.GenericClassType):
                    name = right_node.get_name()
                    pos, ptr, t = struct_t.base.find_method(name, arg_types, lf)
                    t: typ.MethodType
                    if typ.is_generic(t.rtype):
                        return typ.replace_generic_with_real(t.rtype, struct_t.generics)
                    return t.rtype
        elif isinstance(left_t, typ.ArrayType) and isinstance(right_node, NameNode):
            return array_attribute_types(right_node.name, lf)
        elif isinstance(left_t, typ.ClassType) and isinstance(right_node, FunctionCall):  # Class.method(instance, ...)
            arg_types = right_node.arg_types(env, manager)
            name = right_node.get_name()
            pos, ptr, t = left_t.find_method(name, arg_types, lf)
            return t.rtype

        raise errs.TplCompileError(
            f"Left side of dot must be a pointer to class or an array, got {left_t}. ", lf)


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
        elif isinstance(self.left, DollarExpr) or isinstance(self.left, DotExpr):
            right_t.check_convertibility(self.left.evaluated_type(env, tpa.manager), self.lf)
            return self.class_attr_assign(self.left, env, tpa)
        elif isinstance(self.left, IndexingExpr):
            right_t.check_convertibility(self.left.evaluated_type(env, tpa.manager), self.lf)
            return self.array_index_assign(self.left, self.right, env, tpa, self.lf)
        else:
            raise errs.TplCompileError("Cannot assign to a '{}'.".format(self.left.__class__.__name__), self.lf)

        self.right.compile_to(env, tpa, left_addr, left_t.memory_length())
        return left_addr

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return self.right.evaluated_type(env, manager)

    def class_attr_assign(self, dot: DotExpr, env: en.Environment, tpa: tp.TpaOutput):
        attr_ptr, attr_t, const = DotExpr.get_dot_attr_and_type(dot.left, dot.right, env, tpa, dot.lf)
        if const:
            wf = env.get_working_function()
            if not isinstance(wf, typ.MethodType):
                raise errs.TplCompileError(f"Cannot assign constant variable {dot.right}. ", dot.lf)
            if not wf.constructor:
                raise errs.TplCompileError(f"Cannot assign constant variable {dot.right}. ", dot.lf)
        res_addr = self.right.compile(env, tpa)
        tpa.ptr_assign(res_addr, attr_t.length, attr_ptr)
        return res_addr

    @staticmethod
    def array_index_assign(indexing, right, env: en.Environment, tpa: tp.TpaOutput, lf):
        indexed_t = indexing.evaluated_type(env, tpa.manager)
        right_t = right.evaluated_type(env, tpa.manager)
        if not right_t.convertible_to(indexed_t, lf):
            raise errs.TplCompileError(f"Cannot convert type '{right_t}' to '{indexed_t}'. ", lf)

        indexed_ptr = indexing.get_indexed_addr(env, tpa)
        res_addr = right.compile(env, tpa)
        tpa.ptr_assign(res_addr, indexed_t.memory_length(), indexed_ptr)
        return res_addr

    def ptr_assign(self, left: StarExpr, env: en.Environment, tpa: tp.TpaOutput) -> int:
        right_addr = self.right.compile(env, tpa)
        inner_addr = left.value.compile(env, tpa)
        tpa.ptr_assign(right_addr, left.value.evaluated_type(env, tpa.manager).memory_length(), inner_addr)
        return right_addr


class Declaration(BinaryStmt):
    def __init__(self, level, permission, lf):
        super().__init__(":", lf)

        self.level = level
        self.permission = permission

    def get_name(self) -> str:
        return self.get_name_node().name

    def get_name_node(self) -> NameNode:
        if isinstance(self.left, NameNode):
            return self.left
        else:
            raise errs.TplCompileError("Left side of declaration must be a name. ", self.lf)

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
            raise errs.TplCompileError("Left side of declaration must be a name. ", self.lf)

    def __str__(self):
        perm = ""
        if self.permission == PRIVATE:
            perm = "private "
        elif self.permission == PROTECTED:
            perm = "protected "

        if self.level == VAR_VAR:
            level = "var"
        elif self.level == VAR_CONST:
            level = "const"
        else:
            raise Exception("Unexpected error. ")

        return f"BE({perm}{level} {self.left}: {self.right})"


class QuickAssignment(BinaryStmt):
    def __init__(self, lf):
        super().__init__(":=", lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        t = self.right.evaluated_type(env, tpa.manager)
        if not isinstance(self.left, NameNode):
            raise errs.TplCompileError("Left side of ':=' must be name. ", self.lf)

        res_addr = tpa.manager.allocate_stack(t.memory_length())
        env.define_var_set(self.left.name, t, res_addr, self.lf)

        self.right.compile_to(env, tpa, res_addr, t.memory_length())


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
    def __init__(self, name: Expression, params: Line, rtype: Expression, abstract: bool, const: bool,
                 permission: int, body: BlockStmt, lf):
        super().__init__(lf)

        self.name = name
        self.params = params
        self.rtype = rtype
        self.body = body
        self.parent_class: typ.ClassType = None
        self.abstract = abstract
        self.const = const
        self.permission = permission

    def get_simple_name(self) -> str:
        if isinstance(self.name, NameNode):
            return self.name.name
        else:
            raise errs.TplCompileError("Not a named function. ", self.lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        if isinstance(self.name, NameNode):
            self.compile_as(self.name.name, env, tpa)
        else:
            raise errs.TplCompileError("Unexpected function name. ")

    def compile_as(self, simple_name: str, env: en.Environment, tpa: tp.TpaOutput):
        # rtype = self.rtype.definition_type(env, tpa.manager)
        fn_ptr = tpa.manager.allocate_stack(util.PTR_LEN)

        func_type = self.evaluated_type(env, tpa.manager)
        poly_name = typ.function_poly_name(simple_name, func_type.param_types, self.is_method())
        fo = FunctionObject(env, tpa, fn_ptr, self.parent_class, poly_name, self.params, func_type, self.body, self.lf)
        env.define_function(simple_name, func_type, fn_ptr, self.lf)

        tpa.manager.map_function(poly_name, self.lf.file_name, fo)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.FuncType:
        rtype = self.rtype.definition_type(env, manager)
        param_types = []
        for i in range(len(self.params.parts)):
            param = self.params.parts[i]
            if isinstance(param, Declaration):
                pt = param.right.definition_type(env, manager)
                param_types.append(pt)
            else:
                raise errs.TplCompileError("Invalid parameter. ", self.lf)

        if self.parent_class is None:
            if self.abstract:
                raise errs.TplCompileError("Function cannot be abstract. ", self.lf)
            if self.permission != PUBLIC:
                raise errs.TplCompileError("Function cannot be private or protected. ", self.lf)
            return typ.FuncType(param_types, rtype)
        else:
            return typ.MethodType(param_types, rtype, self.parent_class, self.get_simple_name() == "__new__",
                                  self.abstract, self.const, self.permission)

    def is_method(self):
        return self.parent_class is not None

    def __str__(self):
        return "fn {}({}) {} {}".format(self.name, self.params, self.rtype, self.body)


class ClassStmt(Statement):
    def __init__(self, name: str, extensions: Line, templates: Line, abstract: bool, body: BlockStmt, lf):
        super().__init__(lf)

        self.name = name
        # self.class_id = CLASS_ID.increment()
        self.extensions = None
        if extensions is not None:
            self.extensions = extensions
        elif name != "Object":
            self.extensions = Line(lf, NameNode("Object", lf))
        self.template_nodes = templates
        self.body = body
        self.abstract = abstract

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        """
        Compiles a class statement.

        :param env:
        :param tpa:
        :return:
        """
        class_ptr = tpa.manager.allocate_stack(util.PTR_LEN)

        class_name_path = util.class_name_with_path(self.name, self.lf.file_name)
        class_env = en.ClassEnvironment(env)

        # templates
        templates = []  # list of templates
        if self.template_nodes is not None:
            object_t = env.get_type("Object", self.lf)
            assert isinstance(object_t, typ.ClassType)
            for part in self.template_nodes:
                if isinstance(part, NameNode):
                    templates.append(
                        typ.Generic(part.name, object_t, class_name_path))
                elif isinstance(part, FunctionCall):
                    if len(part.args) != 1:
                        raise errs.TplSyntaxError("Invalid syntax. ", self.lf)
                    max_t = part.args[0].evaluated_type(env, tpa.manager)
                    if not isinstance(max_t, typ.ClassType):
                        raise errs.TplCompileError(f"Template {part.args[0]} must extends a class. ", self.lf)
                    templates.append(
                        typ.Generic(part.get_name(), max_t, class_name_path))
                else:
                    raise errs.TplSyntaxError("Template must be name or class extension. ", self.lf)

        # superclasses
        direct_sc = []
        super_generics_lists = {}  # dict of lists
        if self.extensions is not None:
            for ext in self.extensions:
                if isinstance(ext, GenericNode):
                    t = ext.obj.evaluated_type(env, tpa.manager)
                    sup_gens = []
                    for node in ext.generics:
                        if isinstance(node, NameNode):
                            if env.has_name(node.name):
                                sup_gens.append(node.evaluated_type(env, tpa.manager))
                            else:
                                sup_gens.append(typ.Generic.generic_name(class_name_path, node.name))
                        else:
                            raise errs.TplCompileError("Generics in superclass must be names. ", self.lf)
                    super_generics_lists[t] = sup_gens
                else:
                    t = ext.evaluated_type(env, tpa.manager)
                if not isinstance(t, typ.ClassType):
                    raise errs.TplCompileError("Class can only extend classes. ", self.lf)
                direct_sc.append(t)

        # check for duplicate templates
        for tem in templates:
            for sc in direct_sc:
                if tem in sc.templates:
                    raise errs.TplCompileError(f"Duplicate template name '{tem.simple_name()}' already defined in "
                                               f"superclass '{sc.name}'. ", self.lf)
        # find generics inheritance
        # super_generics_map = {}
        templates_map = {}
        for dsc in direct_sc:
            templates_map.update(dsc.templates_map)
        ClassStmt.create_templates_map(templates, direct_sc, templates_map, super_generics_lists, self.lf)
        # print(self.name, templates_map)

        def get_actual(tem_name):
            actual = templates_map[tem_name]
            if isinstance(actual, str):
                return get_actual(actual)
            else:
                return actual

        # print(templates_map)
        for gen in templates_map:
            class_env.define_template(typ.Generic(gen, get_actual(gen), typ.Generic.extract_class_name(gen)), self.lf)

        class_type = typ.ClassType(
            self.name, class_ptr, self.lf.file_name, class_env, direct_sc, templates, templates_map, self.abstract)
        mro = self.make_mro(class_type)
        class_type.mro = mro
        class_env.class_type = class_type

        env.define_const_set(self.name, class_type, class_ptr, self.lf)

        class_wrapper = ClassObject(class_type, self.body, self.abstract, class_env, tpa, self.lf)
        tpa.manager.add_class(class_wrapper)

    @staticmethod
    def create_templates_map(self_templates: [typ.Generic], direct_sc, templates_map, super_map, lf):
        # print(super_map, direct_sc)
        for st in self_templates:
            templates_map[st.full_name()] = st.max_t
        for sc in direct_sc:
            if sc in super_map:
                if len(super_map[sc]) != len(sc.templates):
                    raise errs.TplCompileError("Unequal generics length. ", lf)
                actual = super_map[sc]
                for i in range(len(sc.templates)):
                    gen = sc.templates[i]
                    if isinstance(actual[i], typ.Type):
                        if not actual[i].strong_convertible(gen.max_t):
                            raise errs.TplCompileError("Cannot convert template. ", lf)
                    templates_map[gen.full_name()] = actual[i]

    def make_mro(self, class_type: typ.ClassType):
        def lin(ct: typ.ClassType):
            if len(ct.direct_superclasses) == 0:  # Object
                return [ct]
            to_merge = [lin(sc) for sc in ct.direct_superclasses] + [ct.direct_superclasses]
            return [ct] + merge(to_merge)

        def merge(lst: list):
            out = []
            head_index = 0
            while len(lst) > 0:
                if head_index == len(lst):
                    raise errs.TplCompileError("Inconsistent mro. ", self.lf)
                found = False
                head = lst[head_index][0]
                for i in range(len(lst)):
                    if i != head_index:
                        sub_lst = lst[i]
                        for j in range(1, len(sub_lst)):
                            if sub_lst[j] == head:
                                found = True
                                break
                    if found:
                        break
                if found:
                    head_index += 1
                else:
                    rm_count = 0
                    for i in range(len(lst)):
                        sub_lst = lst[i]
                        new_sub = list(filter(lambda item: item != head, sub_lst))
                        rm_count += (len(sub_lst) - len(new_sub))
                        lst[i] = new_sub
                    lst = list(filter(lambda sl: len(sl) > 0, lst))
                    out.append(head)
                    head_index = 0

            return out

        return lin(class_type)

    def __str__(self):
        if self.template_nodes is None:
            return f"Class {self.name} ({self.extensions}) {self.body}"
        else:
            return f"Class {self.name}<{self.template_nodes}> ({self.extensions}) {self.body}"


class SuperExpr(Statement):
    def __init__(self, lf):
        super().__init__(lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        raise errs.TplCompileError("'super' itself is not a statement. ", self.lf)

    def __str__(self):
        return "super"


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


class GenericNode(Expression):
    def __init__(self, obj: Node, generics: Line, lf):
        super().__init__(lf)

        self.obj = obj
        self.generics = generics

    def get_name(self):
        if isinstance(self.obj, NameNode):
            return self.obj.name
        else:
            raise errs.TplCompileError("Not a named generics. ", self.lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        return self.obj.compile(env, tpa)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return self.definition_type(env, manager)

    def definition_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        class_t = self.obj.definition_type(env, manager)
        if not isinstance(class_t, typ.ClassType):
            raise errs.TplCompileError("Not a class type.", self.lf)

        if len(class_t.templates) != len(self.generics):
            raise errs.TplCompileError(f"Generic class {class_t.name} requires {len(class_t.templates)} generics, "
                                       f"{len(self.generics)} given")

        gen_dict = {}
        for i in range(len(self.generics)):
            gen_t = self.generics[i].evaluated_type(env, manager)
            if not (isinstance(gen_t, typ.ClassType) or
                    isinstance(gen_t, typ.ArrayType) or
                    isinstance(gen_t, typ.Generic)):
                raise errs.TplCompileError(f"Generics must be pointer type, got {gen_t}", self.lf)
            gen = class_t.templates[i]
            if not gen.max_t.superclass_of(gen_t):
                raise errs.TplCompileError(f"Template '{gen.simple_name()}' requires subclass of '{gen.max_t}', "
                                           f"got '{gen_t}'. ",
                                           self.lf)
            gen_dict[gen.full_name()] = gen_t

        templates_map = class_t.templates_map
        full_gen_dict = templates_map.copy()
        full_gen_dict.update(gen_dict)

        has_remain = True
        while has_remain:
            has_remain = False
            for tem_name in full_gen_dict:
                actual = full_gen_dict[tem_name]
                if isinstance(actual, str):
                    has_remain = True
                    full_gen_dict[tem_name] = full_gen_dict[actual]

        # print(full_gen_dict)
        return typ.GenericClassType(class_t, full_gen_dict)

    def __str__(self):
        return f"{self.obj}<{self.generics}>"

    def __eq__(self, other):
        return type(self) == type(other) and self.obj == other.obj and self.generics == other.generics


class FunctionCall(Expression):
    def __init__(self, call_obj: Node, args: Line, lf):
        super().__init__(lf)

        self.call_obj = call_obj
        self.args = args

    def get_name(self):
        if isinstance(self.call_obj, NameNode):
            return self.call_obj.name
        else:
            raise errs.TplCompileError("Not a named function call. ", self.lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        placer = self.call_obj.evaluated_type(env, tpa.manager)
        if isinstance(placer, typ.SpecialCtfType):
            func_class = COMPILE_TIME_FUNCTIONS[placer]
            assert isinstance(func_class, type)
            func = func_class(self.args)
            func_type = func.evaluated_type(env, tpa.manager)
            dst_addr = tpa.manager.allocate_stack(func_type.memory_length())
            func.compile_to(env, tpa, dst_addr)
            return dst_addr
        if isinstance(placer, typ.CompileTimeFunctionType):
            dst_addr = tpa.manager.allocate_stack(placer.rtype.memory_length())
            call_compile_time_function(placer, self.args, env, tpa, dst_addr)
            return dst_addr

        arg_types = self.arg_types(env, tpa.manager)
        if isinstance(placer, typ.FunctionPlacer):  # function defined by 'fn'
            func_type, func_ptr = placer.get_type_and_ptr_call(arg_types, self.lf)
        elif isinstance(placer, typ.CallableType):  # function get by 'getfunc'
            func_type = placer
        else:
            raise errs.TplCompileError(f"Node '{self.call_obj}' not callable because it has type {placer}. ", self.lf)

        rtn_addr = tpa.manager.allocate_stack(func_type.rtype.memory_length())
        self.compile_to(env, tpa, rtn_addr, func_type.rtype.memory_length())
        return rtn_addr

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int, dst_len: int):
        placer = self.call_obj.evaluated_type(env, tpa.manager)
        if isinstance(placer, typ.SpecialCtfType):
            func_class = COMPILE_TIME_FUNCTIONS[placer]
            assert isinstance(func_class, type)
            func = func_class(self.args)
            # func_type = func.evaluated_type(env, tpa.manager)
            func.compile_to(env, tpa, dst_addr)
            return
        if isinstance(placer, typ.CompileTimeFunctionType):
            call_compile_time_function(placer, self.args, env, tpa, dst_addr)
            return

        arg_types = self.arg_types(env, tpa.manager)
        if isinstance(placer, typ.FunctionPlacer):  # function defined by 'fn'
            func_type, func_ptr = placer.get_type_and_ptr_call(arg_types, self.lf)
        elif isinstance(placer, typ.CallableType):  # function get by 'getfunc'
            func_type = placer
            func_ptr = self.call_obj.compile(env, tpa)
        else:
            raise errs.TplCompileError(f"Node '{self.call_obj}' not callable because it has type {placer}. ", self.lf)

        evaluated_args = self.evaluate_args(func_type, env, tpa)
        FunctionCall.call(self.call_obj, evaluated_args, env, tpa, dst_addr, self.lf, func_type, func_ptr)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        placer = self.call_obj.evaluated_type(env, manager)
        if isinstance(placer, typ.SpecialCtfType):
            func = COMPILE_TIME_FUNCTIONS[placer]
            assert isinstance(func, type)
            return func(self.args).evaluated_type(env, manager)
        if isinstance(placer, typ.CompileTimeFunctionType):
            return placer.rtype

        arg_types = self.arg_types(env, manager)
        if isinstance(placer, typ.FunctionPlacer):  # function defined by 'fn'
            func_type, func_ptr = placer.get_type_and_ptr_call(arg_types, self.lf)
        elif isinstance(placer, typ.CallableType):  # function get by 'getfunc'
            func_type = placer
        else:
            raise errs.TplCompileError(f"Node '{self.call_obj}' not callable because it has type {placer}. ", self.lf)

        return func_type.rtype

    @staticmethod
    def call(call_obj, evaluated_args: list,
             env: en.Environment, tpa: tp.TpaOutput, dst_addr: int, lf,
             func_type: typ.CallableType = None,
             fn_ptr: int = -1):

        if isinstance(call_obj, NameNode):
            if func_type is None:
                placer = env.get_type(call_obj.name, lf)
                if not isinstance(placer, typ.FunctionPlacer):
                    raise errs.TplCompileError(f"{call_obj.name} is not a function. ", lf)
                func_type, fn_ptr = placer.get_only()

            if isinstance(func_type, typ.FuncType):
                tpa.call_ptr_function(fn_ptr, evaluated_args, dst_addr, func_type.rtype.length)
            elif isinstance(func_type, typ.NativeFuncType):
                tpa.invoke_ptr(fn_ptr, evaluated_args, dst_addr, func_type.rtype.length)
            else:
                raise errs.TplError("Unexpected error. ", lf)

    @staticmethod
    def call_name(fn_name: str, evaluated_args: list, tpa: tp.TpaOutput, dst_addr: int,
                  lf, func_type):
        if isinstance(func_type, typ.FuncType):
            tpa.call_named_function(fn_name, evaluated_args, dst_addr, func_type.rtype.length)
        else:
            raise errs.TplError("Unexpected error. ", lf)

    @staticmethod
    def call_ptr(fn_ptr: int, evaluated_args: list, tpa: tp.TpaOutput, dst_addr: int,
                 lf, func_type):
        if isinstance(func_type, typ.FuncType):
            tpa.call_ptr_function(fn_ptr, evaluated_args, dst_addr, func_type.rtype.length)
        elif isinstance(func_type, typ.NativeFuncType):
            tpa.invoke_ptr(fn_ptr, evaluated_args, dst_addr, func_type.rtype.length)
        else:
            raise errs.TplError("Unexpected error. ", lf)

    def arg_types(self, env: en.Environment, manager: tp.Manager) -> list:
        return [arg.evaluated_type(env, manager) for arg in self.args]

    def evaluate_args(self, func_type: typ.CallableType, env, tpa, is_method=False) -> list:
        """
        Returns the evaluated arguments, in (addr, length)

        :param func_type:
        :param env:
        :param tpa:
        :param is_method:
        :return:
        """
        diff = 1 if is_method else 0
        evaluated_args = []
        if len(func_type.param_types) != len(self.args) + diff:
            raise errs.TplCompileError(
                f"Function expects {len(func_type.param_types)} params, got {len(self.args) + diff} arguments. ",
                self.lf)
        for i in range(len(func_type.param_types)):
            if i == 0 and is_method:
                continue
            param_t = func_type.param_types[i]
            arg_t: typ.Type = self.args[i - diff].evaluated_type(env, tpa.manager)
            if not arg_t.convertible_to(param_t, self.lf):
                raise errs.TplCompileError("Argument type does not match param type. "
                                           "Expected '{}', got '{}'. ".format(param_t, arg_t), self.lf)
            arg_addr = self.args[i - diff].compile(env, tpa)
            evaluated_args.append((arg_addr, arg_t.length))
        return evaluated_args

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
                    placer = env.get_type(name, node.lf)
                    if not (isinstance(placer, typ.FunctionPlacer) and
                            isinstance(placer.get_only()[0], typ.NativeFuncType)):
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
        if self.condition is None or self.then_expr is None or self.else_expr is None:
            raise errs.TplCompileError("Incomplete if-expr. ", self.lf)
        res_t = self.evaluated_type(env, tpa.manager)
        res_addr = tpa.manager.allocate_stack(res_t.memory_length())
        self.compile_to(env, tpa, res_addr, res_t.memory_length())
        return res_addr

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int, dst_len: int):
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


class FallthroughStmt(Statement):
    def __init__(self, lf):
        super().__init__(lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        label = env.fallthrough()
        tpa.write_format("goto", label)

    def __str__(self):
        return "fallthrough"


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
        module_env = en.ModuleEnvironment(env)
        self.tree.compile(module_env, tpa)
        if module_env.exports is not None:
            env.import_vars(module_env.exports, self.lf)

    def __str__(self):
        return "import {}: {}".format(self.file, self.tree)


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
        return self.get_eval_type(obj_t, env, manager)

    def get_eval_type(self, obj_t, env, manager) -> typ.Type:
        if isinstance(obj_t, typ.ArrayType):
            return obj_t.ele_type
        else:
            raise errs.TplCompileError("Only array type supports indexing. ", self.lf)

    def definition_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        base = self.indexing_obj.definition_type(env, manager)
        if isinstance(base, typ.ClassType) or isinstance(base, typ.Generic):
            base = typ.PointerType(base)
        return typ.ArrayType(base)

    def is_array_initialization(self, env: en.Environment):
        if isinstance(self.indexing_obj, IndexingExpr):
            return self.indexing_obj.is_array_initialization(env)
        elif isinstance(self.indexing_obj, NameNode):
            return env.is_type(self.indexing_obj.name, self.lf)
        else:
            return False

    def indexing(self, env: en.Environment, tpa: tp.TpaOutput) -> int:
        mem_len = self.evaluated_type(env, tpa.manager).memory_length()
        res_addr = tpa.manager.allocate_stack(mem_len)
        indexed_addr = self.get_indexed_addr(env, tpa)

        tpa.value_in_addr_op(indexed_addr, mem_len, res_addr, mem_len)
        return res_addr

    def get_indexed_addr(self, env: en.Environment, tpa: tp.TpaOutput) -> int:
        ele_t = self.evaluated_type(env, tpa.manager)
        array_ptr_addr = self.indexing_obj.compile(env, tpa)
        index_addr = self._get_index_node(env, tpa.manager).compile(env, tpa)

        arith_addr = tpa.manager.allocate_stack(util.INT_LEN)
        tpa.assign(arith_addr, index_addr)
        tpa.i_binary_arith("muli", arith_addr, ele_t.memory_length(), arith_addr)
        tpa.i_binary_arith("addi", arith_addr, util.INT_LEN, arith_addr)  # this step skips the space storing array size

        tpa.binary_arith("addi", array_ptr_addr, arith_addr, util.INT_LEN, util.INT_LEN, arith_addr, util.INT_LEN)
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
        if isinstance(self.value, DollarExpr) or isinstance(self.value, DotExpr) or isinstance(self.value,
                                                                                               IndexingExpr):
            return self.compile_non_suitable(env, tpa)

        vt = self.value.evaluated_type(env, tpa.manager)
        if vt == typ.TYPE_INT:
            op = "addi" if self.op == "++" else "subi"
            v_addr = self.value.compile(env, tpa)
            tpa.i_binary_arith(op, v_addr, 1, v_addr)
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
        if isinstance(self.value, DollarExpr) or isinstance(self.value, DotExpr) or isinstance(self.value,
                                                                                               IndexingExpr):
            return self.compile_attr_op(env, tpa)

        vt = self.value.evaluated_type(env, tpa.manager)
        if vt == typ.TYPE_INT:
            op = "addi" if self.op == "++" else "subi"
            res_addr = tpa.manager.allocate_stack(util.INT_LEN)
            v_addr = self.value.compile(env, tpa)
            tpa.assign(res_addr, v_addr)
            tpa.i_binary_arith(op, v_addr, 1, v_addr)
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


class DoWhileStmt(Statement):
    def __init__(self, lf):
        super().__init__(lf)

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        pass


class CaseStmt(FakeNode):
    def __init__(self, body: BlockStmt, lf, cond: Node = None):
        super().__init__(lf)

        self.cond = cond  # if cond is None, this is a 'default' case
        self.body = body

    def __str__(self):
        if self.cond is None:
            return f"default {self.body}"
        else:
            return f"case {self.cond} {self.body}"

    def __repr__(self):
        return self.__str__()


class CaseExpr(FakeNode):
    def __init__(self, body: Expression, lf, cond: Node = None):
        super().__init__(lf)

        self.cond = cond
        self.body = body

    def __str__(self):
        if self.cond is None:
            return f"default -> {self.body}"
        else:
            return f"case {self.cond} -> {self.body}"

    def __repr__(self):
        return self.__str__()


class SwitchStmt(Statement):
    def __init__(self, cond: Expression, cases: list, default_case: CaseStmt, lf):
        super().__init__(lf)

        self.cond = cond
        self.cases: [CaseExpr] = cases
        self.default_case = default_case

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        # cond_t = self.cond.evaluated_type(env, tpa.manager)
        eq_inst = "eqi"  # todo

        cond_addr = self.cond.compile(env, tpa)
        cond_t = self.cond.evaluated_type(env, tpa.manager)
        arith_addr = tpa.manager.allocate_stack(util.INT_LEN)
        end_case = tpa.manager.label_manager.end_case_label()
        next_case_label = tpa.manager.label_manager.case_label()
        cur_body_label = tpa.manager.label_manager.case_body_label()
        next_body_label = tpa.manager.label_manager.case_body_label()

        for case in self.cases:
            case_cond = case.cond.compile(env, tpa)
            case_cond_t = case.cond.evaluated_type(env, tpa.manager)
            case_env = en.CaseEnvironment(env)
            tpa.binary_arith(eq_inst, cond_addr, case_cond, cond_t.memory_length(), case_cond_t.memory_length(),
                             arith_addr, util.INT_LEN)
            tpa.if_zero_goto(arith_addr, next_case_label)

            tpa.write_format("label", cur_body_label)
            cur_body_label = next_body_label
            next_body_label = tpa.manager.label_manager.case_body_label()
            case.body.compile(case_env, tpa)

            tpa.write_format("goto", end_case)

            tpa.write_format("label", next_case_label)
            next_case_label = tpa.manager.label_manager.case_label()

        if self.default_case is not None:
            tpa.write_format("label", cur_body_label)

            case_env = en.CaseEnvironment(env)
            self.default_case.body.compile(case_env, tpa)

        tpa.write_format("label", end_case)

    def __str__(self):
        return f"switch {self.cond} {self.cases} {self.default_case}"


class SwitchExpr(Expression):
    def __init__(self, cond: Expression, cases: list, default_case: CaseExpr, lf):
        super().__init__(lf)

        self.cond = cond
        self.cases: [CaseExpr] = cases
        self.default_case = default_case

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        res_t = self.evaluated_type(env, tpa.manager)
        res_addr = tpa.manager.allocate_stack(res_t.memory_length())
        self.compile_to(env, tpa, res_addr, res_t.memory_length())
        return res_addr

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int, dst_len: int):
        eq_inst = "eqi"  # todo

        cond_addr = self.cond.compile(env, tpa)
        cond_t = self.cond.evaluated_type(env, tpa.manager)
        arith_addr = tpa.manager.allocate_stack(util.INT_LEN)
        end_case = tpa.manager.label_manager.end_case_label()
        next_case_label = tpa.manager.label_manager.case_label()

        for case in self.cases:
            case_cond = case.cond.compile(env, tpa)
            case_cond_t = case.cond.evaluated_type(env, tpa.manager)
            case_env = en.CaseEnvironment(env)
            tpa.binary_arith(eq_inst, cond_addr, case_cond, cond_t.memory_length(), case_cond_t.memory_length(),
                             arith_addr, util.INT_LEN)
            tpa.if_zero_goto(arith_addr, next_case_label)

            case_body: Expression = case.body
            case_body.compile_to(case_env, tpa, dst_addr, dst_len)

            tpa.write_format("goto", end_case)

            tpa.write_format("label", next_case_label)
            next_case_label = tpa.manager.label_manager.case_label()

        # default case
        case_env = en.CaseEnvironment(env)
        self.default_case.body.compile_to(case_env, tpa, dst_addr, dst_len)

        tpa.write_format("label", end_case)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        t = self.default_case.body.evaluated_type(env, manager)
        for case in self.cases:
            case: CaseExpr
            nt = case.body.evaluated_type(env, manager)
            nt.check_convertibility(t, case.lf)
            t = nt

        return t

    def __str__(self):
        return f"switch {self.cond} {self.cases} {self.default_case}"


class FunctionObject:
    def __init__(self, def_env: en.Environment, tpa, fn_ptr, parent_class, poly_name, params, func_type: typ.FuncType,
                 body, lf):
        self.parent_class = parent_class
        self.fn_ptr = fn_ptr
        self.def_env = def_env
        self.tpa = tpa
        self.poly_name = poly_name
        self.func_type = func_type
        self.params = params
        self.body = body
        self.lf = lf

    def compile(self):
        if self.parent_class is None:
            scope = en.FunctionEnvironment(self.def_env, self.poly_name, self.func_type)
        else:
            scope = en.MethodEnvironment(self.def_env, self.poly_name, self.func_type, self.parent_class)
        self.tpa.manager.push_stack()

        body_out = tp.TpaOutput(self.tpa.manager)

        param_types = []
        for i in range(len(self.params.parts)):
            param = self.params.parts[i]
            if isinstance(param, Declaration):
                pt = param.right.definition_type(self.def_env, self.tpa.manager)
                param_types.append(pt)
                param.compile(scope, body_out)

        if self.body is not None:
            # check return
            complete_return = self.body.return_check()
            if not complete_return:
                if not self.func_type.rtype.is_void():
                    raise errs.TplCompileError(f"Function '{self.poly_name}' missing a return statement. ", self.lf)

            # compiling
            body_out.add_function(self.poly_name, self.lf.file_name, self.fn_ptr, self.parent_class)
            push_index = body_out.add_indefinite_push()
            self.body.compile(scope, body_out)

            # ending
            if self.func_type.rtype.is_void():
                body_out.return_func()
            body_out.end_func()

            stack_len = body_out.manager.sp - body_out.manager.blocks[-1]
            body_out.modify_indefinite_push(push_index, stack_len)

        self.tpa.manager.restore_stack()
        body_out.local_generate()

        return body_out.result()


class ClassObject:
    def __init__(self, class_type: typ.ClassType, body, abstract: bool,
                 class_env: en.ClassEnvironment, tpa, lf):
        self.class_type = class_type
        self.body = body
        self.abstract = abstract
        self.class_env = class_env
        self.tpa = tpa
        self.lf = lf

        self.local_method_full_names = []

    def compile(self):
        mro = self.class_type.mro

        method_defs = []
        if len(mro) == 1:  # Object itself
            pos = util.INT_LEN
        else:
            pos = mro[1].memory_length()
            for m_name in mro[1].methods:
                self.class_type.methods[m_name] = mro[1].methods[m_name].copy()
            self.class_type.method_rank.extend(mro[1].method_rank)

        # the class pointer
        self.class_type.fields["__class__"] = 0, typ.TYPE_INT, self.class_type, True, PUBLIC

        def eval_declaration(dec: Declaration, cur_field_pos):
            dec_name = dec.get_name()
            if self.class_type.has_field(dec_name):
                raise errs.TplCompileError(
                    f"Name '{dec_name}' already defined in class '{self.class_type.name}'. ", self.lf)
            t = dec.right.definition_type(self.class_env, self.tpa.manager)
            self.class_type.fields[dec_name] = cur_field_pos, t, self.class_type, dec.level == VAR_CONST, dec.permission
            return t.memory_length()

        for line in self.body:
            for part in line:
                if isinstance(part, Declaration):
                    pos += eval_declaration(part, pos)
                    continue
                elif isinstance(part, Assignment):
                    if isinstance(part.left, Declaration):
                        pos += eval_declaration(part.left, pos)
                        ass = Assignment(part.lf)
                        this_dot = DotExpr(part.lf)
                        this_dot.left = NameNode("this", part.lf)
                        this_dot.right = part.left.get_name_node()
                        ass.left = this_dot
                        ass.right = part.right
                        self.class_type.initializers.append(ass)
                        continue
                elif isinstance(part, FunctionDef):
                    part.parent_class = self.class_type
                    method_defs.append(part)
                    continue

                raise errs.TplCompileError(
                    f"Class body should only contain attributes and methods, but got a '{part}'. ", self.lf)

        self.class_type.length = pos

        # check if there is a constructor
        self.add_constructor_if_none(method_defs, self.class_type)

        # update methods
        method_id = len(self.class_type.method_rank)  # id of method in this class
        for method_def in method_defs:
            # check method params and content
            self.check_method_def(method_def, self.class_type)

            method_def.compile(self.class_env, self.tpa)
            name = method_def.get_simple_name()

            placer: typ.FunctionPlacer = self.class_env.get_type(name, self.lf)
            method_t = method_def.evaluated_type(self.class_env, self.tpa.manager)
            method_ptr = placer.poly[method_t]

            self.local_method_full_names.append(
                util.name_with_path(
                    typ.function_poly_name(name, method_t.param_types, True),
                    self.class_type.file_path,
                    self.class_type
                ))

            if not isinstance(method_t, typ.MethodType):
                raise errs.TplCompileError("Unexpected method. ", self.lf)

            if not self.abstract and method_t.abstract:
                raise errs.TplCompileError(
                    f"Class '{self.class_type.name}' is not abstract, but has abstract method '{name}'. ", method_def.lf
                )

            if name in self.class_type.methods:
                if method_t in self.class_type.methods[name]:  # overriding
                    m_pos, m_ptr, m_t = self.class_type.methods[name][method_t]
                    # print(f"class {self.class_type.name} overrides method {name} at {m_ptr}, new ptr {method_ptr}")
                    if name != "__new__":
                        if not method_t.strong_convertible(m_t):
                            # print(method_t.param_types[0].base)
                            # print(m_t.param_types[0])
                            raise errs.TplCompileError(
                                f"Method '{name}' in class '{self.class_type.name}' "
                                f"overrides its super method in class '{m_t.defined_class.name}', "
                                f"but has incompatible parameter or return type. ", method_def.lf)
                        if method_t.permission > m_t.permission:
                            raise errs.TplCompileError(
                                f"Method '{name}' in class '{self.class_type.name}' "
                                f"overrides its super method in class '{m_t.defined_class.name}', "
                                f"but has weaker access. ", method_def.lf)

                    if m_t.const:
                        raise errs.TplCompileError(
                            f"Method '{name}' is const, which cannot be overridden. ", method_def.lf
                        )
                    self.class_type.methods[name][method_t] = m_pos, method_ptr, method_t
                else:  # polymorphism
                    poly: util.NaiveDict = self.class_type.methods[name]
                    self.class_type.method_rank.append((name, method_t))
                    poly[method_t] = method_id, method_ptr, method_t
                    method_id += 1
            else:
                self.class_type.method_rank.append((name, method_t))
                poly = util.NaiveDict(typ.params_eq_methods)
                poly[method_t] = method_id, method_ptr, method_t
                self.class_type.methods[name] = poly
                method_id += 1

        # # check if all abstract methods are overridden
        if not self.abstract:
            for poly in self.class_type.methods.values():
                for method_id, method_ptr, method_t in poly.values:
                    if method_t.abstract:
                        raise errs.TplCompileError(
                            f"Class '{self.class_type.name}' "
                            f"does not override all abstract methods of its superclasses. ",
                            self.lf
                        )

    def check_method_def(self, method: FunctionDef, class_type: typ.ClassType):
        desired_this_t_node = StarExpr(method.lf)
        name_node = NameNode(class_type.name, method.lf)
        if len(class_type.templates) > 0:
            gen_line = Line(method.lf)
            for gen in class_type.templates:
                gen_line.parts.append(NameNode(gen.simple_name(), method.lf))
            gen_node = GenericNode(name_node, gen_line, method.lf)
            desired_this_t_node.value = gen_node
        else:
            desired_this_t_node.value = name_node

        insert_this = True
        if len(method.params) > 0:
            first_param = method.params[0]
            if isinstance(first_param, Declaration) and \
                    isinstance(first_param.left, NameNode) and \
                    first_param.left.name == "this":
                if first_param.right != desired_this_t_node:
                    raise errs.TplCompileError(f"Parameter 'this' must be {desired_this_t_node}, "
                                               f"got {first_param.right}. ",
                                               self.lf)
                insert_this = False
        if insert_this:
            dec = Declaration(VAR_CONST, PUBLIC, method.lf)
            dec.left = NameNode("this", method.lf)
            dec.right = desired_this_t_node
            method.params.parts.insert(0, dec)

        if method.get_simple_name() == "__new__":
            if class_type.name != "Object" and method.get_simple_name() == "__new__":
                insert_super = True
                first_stmt = method.body.get_first_content()
                # print(first_stmt)
                if first_stmt is not None:
                    if isinstance(first_stmt, DotExpr) and \
                            isinstance(first_stmt.left, SuperExpr) and \
                            isinstance(first_stmt.right, FunctionCall) and \
                            isinstance(first_stmt.right.call_obj, NameNode) and \
                            first_stmt.right.call_obj.name == "__new__":
                        insert_super = False
                if insert_super:
                    dot = DotExpr(method.lf)
                    dot.left = SuperExpr(method.lf)
                    dot.right = FunctionCall(NameNode("__new__", method.lf), Line(method.lf), method.lf)
                    method.body.lines.insert(0, Line(method.lf, dot))
            initializer_index = 0 if class_type.name == "Object" else 1
            method.body.insert_at(initializer_index, class_type.initializers)

    def add_constructor_if_none(self, method_defs: [FunctionDef], class_type: typ.ClassType):
        no_constructor = len(list(filter(lambda fd: fd.get_simple_name() == "__new__", method_defs))) == 0
        if no_constructor:
            const = FunctionDef(NameNode("__new__", self.lf),
                                Line(self.lf),
                                NameNode("void", self.lf),
                                False,
                                False,
                                PUBLIC,
                                BlockStmt(self.lf),
                                self.lf)
            const.parent_class = class_type
            method_defs.append(const)


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

INT_BIT_TABLE = {
    "<<": "lshift",
    ">>": "rshift",
    ">>>": "rshiftl",
    "&": "and",
    "|": "or",
    "^": "xor"
}

FLOAT_ARITH_TABLE = {
    "+": "addf",
    "-": "subf",
    "*": "mulf",
    "/": "divf",
    "%": "modf"
}

FLOAT_LOGIC_TABLE = {
    "==": "eqf",
    "!=": "nef",
    ">": "gtf",
    "<": "ltf",
    ">=": "gef",
    "<=": "lef"
}


def int_int_to_int(op: str, left_addr: int, right_addr: int, res_addr: int, tpa: tp.TpaOutput):
    if op in INT_ARITH_TABLE:
        op_inst = INT_ARITH_TABLE[op]
    elif op in INT_LOGIC_TABLE:
        op_inst = INT_LOGIC_TABLE[op]
    elif op in INT_BIT_TABLE:
        op_inst = INT_BIT_TABLE[op]
    else:
        raise errs.TplCompileError("No such binary operator '" + op + "'. ")
    tpa.binary_arith(op_inst, left_addr, right_addr, util.INT_LEN, util.INT_LEN, res_addr, util.INT_LEN)


def float_float_to_float(op: str, left_addr: int, right_addr: int, res_addr: int, tpa: tp.TpaOutput):
    if op in FLOAT_ARITH_TABLE:
        op_inst = FLOAT_ARITH_TABLE[op]
    elif op in FLOAT_LOGIC_TABLE:
        op_inst = FLOAT_LOGIC_TABLE[op]
    else:
        raise errs.TplCompileError("No such binary operator '" + op + "'. ")
    tpa.binary_arith(op_inst, left_addr, right_addr, util.FLOAT_LEN, util.FLOAT_LEN, res_addr, util.FLOAT_LEN)


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
    t = args[0].definition_type(env, tpa.manager)
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
        tpa.i_binary_arith("addi", arr_ptr, i * util.INT_LEN, arith_addr)  # (i - 1) * INT_LEN + INT_LEN
        arg_addr = arg.compile(env, tpa)
        tpa.ptr_assign(arg_addr, arg_t.memory_length(), arith_addr)

    sizeof_name = NameNode("sizeof", args.lf)
    sizeof_call = FunctionCall(sizeof_name, Line(args.lf, args[0]), args.lf)
    sizeof_res = sizeof_call.compile(env, tpa)

    fn_name = NameNode("heap_array", args.lf)
    req = RequireStmt(fn_name, args.lf)
    req.compile(env, tpa)
    FunctionCall.call(fn_name, [(sizeof_res, util.INT_LEN), (arr_ptr, util.PTR_LEN)],
                      env, tpa, dst_addr, args.lf)


class SpecialCtf:
    def __init__(self, args: Line):
        self.args = args

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int):
        raise NotImplementedError()

    def evaluated_type(self, env: en.Environment, manager: tp.Manager):
        raise NotImplementedError()


class CtfGetFunc(SpecialCtf):
    def __init__(self, args: Line):
        super().__init__(args)

    def get_func(self, env, manager) -> (typ.FuncType, int):
        if len(self.args) > 0:
            func_node = self.args[0]
            if isinstance(func_node, NameNode):
                placer = env.get_type(func_node.name, self.args.lf)
                if isinstance(placer, typ.FunctionPlacer):
                    arg_types = []
                    for i in range(1, len(self.args)):
                        arg_types.append(self.args[i].evaluated_type(env, manager))
                    t, addr = placer.get_type_and_ptr_call(arg_types, self.args.lf)
                    return t, addr
            elif isinstance(func_node, DotExpr) and isinstance(func_node.right, NameNode):
                class_t = func_node.left.evaluated_type(env, manager)
                if isinstance(class_t, typ.ClassType):
                    arg_types = [None]
                    for i in range(1, len(self.args)):
                        arg_types.append(self.args[i].evaluated_type(env, manager))
                    method_id, method_ptr, method_t = class_t.find_method(func_node.right.name, arg_types, self.args.lf)
                    return method_t, method_ptr
        raise errs.TplCompileError(f"Cannot make call {self}. ", self.args.lf)

    def compile_to(self, env: en.Environment, tpa: tp.TpaOutput, dst_addr: int):
        t, ptr = self.get_func(env, tpa.manager)
        tpa.assign(dst_addr, ptr)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager):
        t, ptr = self.get_func(env, manager)
        return t

    def __str__(self):
        return "getfunc(" + str(self.args) + ")"


COMPILE_TIME_FUNCTIONS = {
    typ.CompileTimeFunctionType("sizeof", typ.TYPE_INT): ctf_sizeof,
    typ.CompileTimeFunctionType("cprint", typ.TYPE_VOID): ctf_cprint,
    typ.CompileTimeFunctionType("cprintln", typ.TYPE_VOID): ctf_cprintln,
    typ.CompileTimeFunctionType("array", typ.TYPE_VOID_PTR): ctf_array,
    typ.SpecialCtfType("getfunc"): CtfGetFunc
}


def call_compile_time_function(func_t: typ.CompileTimeFunctionType, arg: Line,
                               env: en.Environment, tpa: tp.TpaOutput, dst_addr: int):
    f = COMPILE_TIME_FUNCTIONS[func_t]
    if f.__code__.co_argcount == 3:
        f(arg, env, tpa)
    else:
        f(arg, env, tpa, dst_addr)
