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


class Statement(Node, ABC):
    def __init__(self, lf):
        super().__init__(lf)

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        raise errs.TplTypeError("Statements do not evaluate a type. ", self.lf)


class Line(Expression):
    def __init__(self, lf):
        super().__init__(lf)

        self.parts: [Node] = []

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

    def __getitem__(self, item):
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

    def __getitem__(self, item):
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
                ife = IfExpr(self.left, self.right, IntLiteral(util.FALSE_POS, self.lf), self.lf)
                if not ife.evaluated_type(env, tpa.manager).convertible_to(typ.TYPE_INT, self.lf):
                    raise errs.TplCompileError("Cannot convert {} to {}. ".format(ife, typ.TYPE_INT), self.lf)
                return ife.compile(env, tpa)
            elif self.op == "or":
                ife = IfExpr(self.left, IntLiteral(util.TRUE_POS, self.lf), self.right, self.lf)
                if not ife.evaluated_type(env, tpa.manager).convertible_to(typ.TYPE_INT, self.lf):
                    raise errs.TplCompileError("Cannot convert {} to {}. ".format(ife, typ.TYPE_INT), self.lf)
                return ife.compile(env, tpa)
            else:
                raise errs.TplCompileError("Unexpected lazy operator. ", self.lf)

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


class BinaryOperatorAssignment(BinaryExpr):
    def __init__(self, op: str, op_type: int, lf):
        super().__init__(op, lf)

        self.op_type = op_type

    def compile(self, env: en.Environment, tpa: tp.TpaOutput):
        pass

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        pass


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
            if isinstance(struct_t, typ.StructType)  and isinstance(self.right, NameNode):
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
            return self.array_index_assign(self.left, env, tpa)
        else:
            raise errs.TplCompileError("Cannot assign to a '{}'.".format(self.left.__class__.__name__), self.lf)

        right_addr = self.right.compile(env, tpa)
        tpa.assign(left_addr, right_addr)
        return right_addr

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        return self.right.evaluated_type(env, manager)

    def struct_attr_assign(self, dot, env: en.Environment, tpa: tp.TpaOutput):
        attr_ptr, attr_t = dot.get_attr_ptr_and_type(env, tpa)
        res_addr = self.right.compile(env, tpa)
        tpa.ptr_assign(res_addr, attr_ptr)
        return res_addr

    def array_index_assign(self, indexing, env: en.Environment, tpa: tp.TpaOutput):
        indexed_t = indexing.evaluated_type(env, tpa.manager)
        right_t = self.right.evaluated_type(env, tpa.manager)
        if isinstance(right_t, typ.ArrayType):
            raise errs.TplCompileError("Cannot assign an array as an element. ", self.lf)
        if not right_t.convertible_to(indexed_t, self.lf):
            raise errs.TplCompileError(f"Cannot convert type '{right_t}' to '{indexed_t}'. ", self.lf)

        indexed_ptr = indexing.get_indexed_addr(env, tpa)
        res_addr = self.right.compile(env, tpa)
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
        if isinstance(self.call_obj, NameNode):
            rtn_addr = tpa.manager.allocate_stack(func_type.rtype.length)
            if isinstance(func_type, typ.FuncType):
                # if env.is_named_function(self.call_obj.name, self.lf):
                #     tpa.call_named_function(self.call_obj.name, evaluated_args, rtn_addr, func_type.rtype.length)
                # else:
                fn_ptr = env.get(self.call_obj.name, self.lf)
                tpa.call_ptr_function(fn_ptr, evaluated_args, rtn_addr, func_type.rtype.length)
            elif isinstance(func_type, typ.NativeFuncType):
                fn_ptr = env.get(self.call_obj.name, self.lf)
                tpa.invoke_ptr(fn_ptr, evaluated_args, rtn_addr, func_type.rtype.length)
            else:
                raise errs.TplError("Unexpected error. ", self.lf)
            return rtn_addr

    def evaluated_type(self, env: en.Environment, manager: tp.Manager) -> typ.Type:
        func_type = self.call_obj.evaluated_type(env, manager)
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

    def require(self, node: Node, env: en.Environment, tpa: tp.TpaOutput):
        if isinstance(node, BlockStmt):
            for line in node.lines:
                self.require(line, env, tpa)
        elif isinstance(node, Line):
            for part in node.parts:
                self.require(part, env, tpa)
        elif isinstance(node, NameNode):
            name = node.name
            if name in typ.NATIVE_FUNCTIONS:
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
        cond_addr = self.condition.compile(env, tpa)
        res_t = self.evaluated_type(env, tpa.manager)
        res_addr = tpa.manager.allocate_stack(res_t.length)

        else_label = tpa.manager.label_manager.else_label()
        endif_label = tpa.manager.label_manager.endif_label()

        tpa.if_zero_goto(cond_addr, else_label)

        if_env = en.BlockEnvironment(env)
        then_addr = self.then_expr.compile(if_env, tpa)
        tpa.assign(res_addr, then_addr)

        tpa.write_format("goto", endif_label)
        tpa.write_format("label", else_label)

        else_env = en.BlockEnvironment(env)
        else_addr = self.else_expr.compile(else_env, tpa)
        tpa.assign(res_addr, else_addr)

        tpa.write_format("label", endif_label)
        return res_addr

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
            return self.array_initialization(env, tpa)
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

    def array_initialization(self, env: en.Environment, tpa: tp.TpaOutput) -> int:
        res_addr = tpa.manager.allocate_stack(util.PTR_LEN)

        dimensions = []
        node = self
        while isinstance(node, IndexingExpr):
            dimensions.insert(0, node._get_index_literal(env, tpa.manager))
            node = node.indexing_obj

        root_t = node.evaluated_type(env, tpa.manager)

        self.array_creation(res_addr, root_t, dimensions, 0, env, tpa)

        return res_addr

    def array_creation(self, this_ptr_addr, atom_t: typ.Type, dimensions: list, index_in_dim: int,
                       env: en.Environment, tpa: tp.TpaOutput):

        if index_in_dim == len(dimensions) - 1:
            ele_len = atom_t.memory_length()
        else:
            ele_len = util.PTR_LEN
        arr_size = dimensions[index_in_dim]
        arr_addr = tpa.manager.allocate_stack(ele_len * arr_size + util.INT_LEN)
        tpa.assign_i(arr_addr, arr_size)
        tpa.take_addr(arr_addr, this_ptr_addr)

        if index_in_dim == len(dimensions) - 1:
            pass
        else:
            first_ele_addr = arr_addr + util.INT_LEN
            for i in range(arr_size):
                self.array_creation(first_ele_addr + i * util.PTR_LEN, atom_t, dimensions, index_in_dim + 1, env, tpa)

    # def allocate_one_array(self, ptr_to_array, ele_size, ele_count, tpa: tp.TpaOutput):
    #     array_addr = tpa.manager.allocate_stack(ele_size * ele_count + util.INT_LEN)
    #     tpa.assign_i(array_addr, ele_count)
    #     tpa.take_addr(array_addr, ptr_to_array)

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

        # arg_node = self._get_index_node()
        # arg_t = arg_node.evaluated_type(env, tpa.manager)
        # if arg_t != typ.TYPE_INT:
        #     raise errs.TplCompileError("Index must be int. ", self.lf)
        # return self._get_abs_addr_of_index(env, tpa)

    # def _get_abs_addr_of_index(self, env: en.Environment, tpa: tp.TpaOutput) -> int:
    #     """
    #     Returns an address, which stores the absolute addr of the
    #     返回一个相对地址，在此相对地址中存有“数组第i个值”的地址
    #     """
    #     res_addr = tpa.manager.allocate_stack(util.INT_LEN)
    #     acc_addr = tpa.manager.allocate_stack(util.INT_LEN)
    #     arith_addr = tpa.manager.allocate_stack(util.INT_LEN)
    #
    #     orig_t = self._get_orig_type(env, tpa.manager)
    #
    #     base = self
    #     base_t = orig_t
    #     while isinstance(base, IndexingExpr):
    #         if not isinstance(base_t, typ.ArrayType):
    #             raise errs.TplCompileError("Cannot take index on non-array type. ", self.lf)
    #
    #         base_t = base_t.base
    #         cur_arg = base._get_index_node()
    #         cur_unit_len = base_t.memory_length()
    #
    #         tpa.assign(arith_addr, cur_arg.compile(env, tpa))
    #         tpa.binary_arith_i("muli", arith_addr, cur_unit_len, arith_addr)
    #         tpa.binary_arith("addi", acc_addr, arith_addr, acc_addr)
    #
    #         base = base.indexing_obj
    #
    #     if isinstance(base_t, typ.ArrayType):
    #         raise errs.TplCompileError("Cannot take array as value. ", self.lf)
    #
    #     array_addr = base.compile(env, tpa)
    #
    #     tpa.take_addr(array_addr, res_addr)
    #     tpa.binary_arith("addi", res_addr, acc_addr, res_addr)
    #     return res_addr

    def _get_atom_type(self, env, manager):
        if isinstance(self.indexing_obj, IndexingExpr):
            return self.indexing_obj._get_atom_type(env, manager)
        else:
            return self.indexing_obj.evaluated_type(env, manager)

    def _get_index_node(self, env, manager) -> Node:
        if len(self.args) != 1:
            raise errs.TplCompileError("Array initialization or indexing must contain exactly one int element. ",
                                       self.lf)
        arg: Node = self.args[0]
        if arg.evaluated_type(env, manager) != typ.TYPE_INT:
            raise errs.TplCompileError("Array initialization or indexing must contain exactly one int element. ",
                                       self.lf)
        return arg

    def _get_index_literal(self, env, manager: tp.Manager):
        node = self._get_index_node(env, manager)
        if not isinstance(node, IntLiteral):
            raise errs.TplCompileError("Array type declaration must be an int literal. ", self.lf)
        return util.bytes_to_int(manager.literal[node.lit_pos: node.lit_pos + util.INT_LEN])

    def __str__(self):
        return f"{self.indexing_obj}[{self.args}]"


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


def array_attribute_types(attr_name: str, lf):
    if attr_name == "length":
        return typ.TYPE_INT

    raise errs.TplCompileError(f"Array does not have attribute '{attr_name}'. ", lf)
