import compilers.errors as errs
import compilers.util as util
import compilers.types as typ


def register(num) -> str:
    if isinstance(num, int):
        return "%" + str(num)
    else:
        raise errs.TplCompileError("Cannot compile '{}' to register. ".format(num))


def address(num: int) -> str:
    if isinstance(num, int):
        return "$" + str(num)
    else:
        raise errs.TplCompileError("Cannot compile '{}' to address. ".format(num))


def number(num: int) -> str:
    if isinstance(num, int):
        return str(num)
    else:
        raise errs.TplCompileError("Cannot compile '{}' to number. ".format(num))


def load_of_len(length: int) -> str:
    if length == util.INT_LEN:
        return "load"
    elif length == util.CHAR_LEN:
        return "loadc"
    else:
        return "loadb"


def store_of_len(length: int) -> str:
    if length == util.INT_LEN:
        return "store"
    elif length == util.CHAR_LEN:
        return "storec"
    else:
        return "storeb"


def store_abs_of_len(length: int) -> str:
    if length == util.INT_LEN:
        return "store_abs"
    elif length == util.CHAR_LEN:
        return "storec_abs"
    else:
        return "storeb_abs"


class LabelManager:
    def __init__(self):
        self._else_count = 0
        self._endif_count = 0
        self._loop_title_count = 0
        self._end_loop_count = 0
        self._general_count = 0
        self._case_count = 0
        self._case_body_count = 0
        self._end_case_count = 0

    def endif_label(self):
        n = self._endif_count
        self._endif_count += 1
        return "ENDIF_" + str(n)

    def else_label(self):
        n = self._else_count
        self._else_count += 1
        return "ELSE_" + str(n)

    def loop_title_label(self):
        n = self._loop_title_count
        self._loop_title_count += 1
        return "LOOP_TITLE_" + str(n)

    def end_loop_label(self):
        n = self._end_loop_count
        self._end_loop_count += 1
        return "END_LOOP_" + str(n)

    def general_label(self):
        n = self._general_count
        self._general_count += 1
        return "LABEL_" + str(n)

    def case_label(self):
        n = self._case_count
        self._case_count += 1
        return "CASE_" + str(n)

    def case_body_label(self):
        n = self._case_body_count
        self._case_body_count += 1
        return "CASE_BODY_" + str(n)

    def end_case_label(self):
        n = self._end_case_count
        self._end_case_count += 1
        return "END_CASE_" + str(n)


class Manager:
    def __init__(self, literal: bytes):
        self.literal = literal
        self.blocks = []
        self.available_regs = [7, 6, 5, 4, 3, 2, 1, 0]
        self.gp = util.STACK_SIZE
        self.sp = util.INT_LEN + 1
        self.functions_map = {}
        self.class_headers = []  # class type
        self.label_manager = LabelManager()

    def allocate_stack(self, length):
        if len(self.blocks) == 0:
            addr = self.gp
            self.gp += length
        else:
            addr = self.sp - self.blocks[-1]
            self.sp += length
        return addr

    def push_stack(self):
        self.blocks.append(self.sp)

    def restore_stack(self):
        self.sp = self.blocks.pop()

    def require_regs(self, count):
        if len(self.available_regs) < count:
            raise errs.TplCompileError("Virtual machine does not have enough registers. ")
        return [self.available_regs.pop() for _ in range(count)]

    def require_reg(self):
        if len(self.available_regs) == 0:
            raise errs.TplCompileError("Virtual machine does not have enough registers. ")
        return self.available_regs.pop()

    def append_regs(self, *regs):
        for reg in regs:
            self.available_regs.append(reg)

    def map_function(self, name: str, file_path, function_object):
        self.functions_map[util.name_with_path(name, file_path, function_object.parent_class)] = function_object

    def add_class(self, class_type: typ.ClassType):
        self.class_headers.append(class_type)

    def global_length(self):
        return self.gp - util.STACK_SIZE


class TpaOutput:
    def __init__(self, manager: Manager, is_global=False):
        self.manager: Manager = manager
        self.is_global = is_global
        self.output = ["entry"] if is_global else []

    def add_class(self):
        pass

    def add_function(self, name, file_path, fn_ptr, clazz):
        self.output.append("fn " + util.name_with_path(name, file_path, clazz) + " " + address(fn_ptr))
        self.write_format("push_fp")

    def add_indefinite_push(self) -> int:
        self.output.append("push")
        return len(self.output) - 1

    def modify_indefinite_push(self, index, length):
        push = self._format("push", length)
        self.output[index] = push

    def end_func(self):
        self.write_format("stop")
        self.output.append("")

    def return_func(self):
        self.write_format("pull_fp")
        self.write_format("ret")

    def assign(self, dst_addr, src_addr):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("load", register(reg1), address(src_addr))
        self.write_format("iload", register(reg2), address(dst_addr))
        self.write_format("store", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def assign_char(self, dst_addr, src_addr):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("loadc", register(reg1), address(src_addr))
        self.write_format("iload", register(reg2), address(dst_addr))
        self.write_format("storec", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def assign_i(self, dst_addr, value):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("iload", register(reg1), address(value))
        self.write_format("iload", register(reg2), address(dst_addr))
        self.write_format("store", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def load_literal(self, dst_addr, lit_pos):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("load_lit", register(reg1), address(lit_pos))
        self.write_format("iload", register(reg2), address(dst_addr))
        self.write_format("store", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def load_char_literal(self, dst_addr, lit_pos):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("loadc_lit", register(reg1), address(lit_pos))
        self.write_format("iload", register(reg2), address(dst_addr))
        self.write_format("storec", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def load_byte_literal(self, dst_addr, lit_pos):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("loadb_lit", register(reg1), address(lit_pos))
        self.write_format("iload", register(reg2), address(dst_addr))
        self.write_format("storeb", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def load_literal_ptr(self, dst_addr, lit_pos):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("lit_abs", register(reg1), address(lit_pos))
        self.write_format("iload", register(reg2), address(dst_addr))
        self.write_format("store", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def convert_char_to_int(self, dst_addr, src_addr):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("loadc", register(reg1), address(src_addr))
        self.write_format("iload", register(reg2), address(dst_addr))
        self.write_format("store", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def convert_int_to_char(self, dst_addr, src_addr):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("load", register(reg1), address(src_addr))
        self.write_format("iload", register(reg2), address(dst_addr))
        self.write_format("storec", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def convert_byte_to_int(self, dst_addr, src_addr):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("loadb", register(reg1), address(src_addr))
        self.write_format("iload", register(reg2), address(dst_addr))
        self.write_format("store", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def convert_int_to_byte(self, dst_addr, src_addr):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("load", register(reg1), address(src_addr))
        self.write_format("iload", register(reg2), address(dst_addr))
        self.write_format("storeb", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def convert_float_to_int(self, dst_addr, src_addr):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("load", register(reg1), address(src_addr))
        self.write_format("f_to_i", register(reg1))
        self.write_format("iload", register(reg2), address(dst_addr))
        self.write_format("store", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def convert_int_to_float(self, dst_addr, src_addr):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("load", register(reg1), address(src_addr))
        self.write_format("i_to_f", register(reg1))
        self.write_format("iload", register(reg2), address(dst_addr))
        self.write_format("store", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def return_value(self, src_addr):
        reg1 = self.manager.require_reg()

        self.write_format("load", register(reg1), address(src_addr))
        self.write_format("put_ret", register(reg1))

        self.manager.append_regs(reg1)

    def return_char_value(self, src_addr):
        reg1 = self.manager.require_reg()

        self.write_format("loadc", register(reg1), address(src_addr))
        self.write_format("put_ret", register(reg1))

        self.manager.append_regs(reg1)

    def binary_arith(self, op_inst: str, left: int, right: int, left_len: int, right_len: int, res: int, res_len: int):
        reg1, reg2 = self.manager.require_regs(2)

        # result length will always be INT_LEN
        self.write_format(load_of_len(left_len), register(reg1), address(left))
        self.write_format(load_of_len(right_len), register(reg2), address(right))
        self.write_format(op_inst, register(reg1), register(reg2))
        self.write_format("iload", register(reg2), number(res))
        self.write_format(store_of_len(res_len), register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def i_binary_arith(self, op_inst: str, left: int, right_value: int, res: int):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("load", register(reg1), address(left))
        self.write_format("iload", register(reg2), number(right_value))
        self.write_format(op_inst, register(reg1), register(reg2))
        self.write_format("iload", register(reg2), number(res))
        self.write_format("store", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def unary_arith(self, op_inst: str, value: int, res: int):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("load", register(reg1), address(value))
        self.write_format(op_inst, register(reg1))
        self.write_format("iload", register(reg2), number(res))
        self.write_format("store", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def to_abs(self, value_addr, res_addr):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("load", register(reg1), address(value_addr))
        self.write_format("iload", register(reg2), number(res_addr))
        self.write_format("astore", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def take_addr(self, value_addr: int, res_addr: int):
        """
        This instruction set just convert 'value_addr' to absolute addr and write it to 'res_addr'

        :param value_addr:
        :param res_addr:
        :return:
        """
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("aload", register(reg1), address(value_addr))
        self.write_format("iload", register(reg2), number(res_addr))
        self.write_format("store", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def value_in_addr_op(self, ptr_addr: int, length: int, res_addr: int, res_len: int):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("load", register(reg1), address(ptr_addr))
        if length == util.INT_LEN:
            self.write_format("rload_abs", register(reg2), register(reg1))
        elif length == util.CHAR_LEN:
            self.write_format("rloadc_abs", register(reg2), register(reg1))
        else:
            self.write_format("rloadb_abs", register(reg2), register(reg1))
        self.write_format("iload", register(reg1), number(res_addr))
        self.write_format(store_of_len(res_len), register(reg1), register(reg2))

        self.manager.append_regs(reg2, reg1)

    def ptr_assign(self, value_addr: int, value_len: int, ptr_addr: int):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("load", register(reg1), address(ptr_addr))
        self.write_format("load", register(reg2), address(value_addr))
        self.write_format(store_abs_of_len(value_len), register(reg1), register(reg2))

        self.manager.append_regs(reg2, reg1)

    def i_ptr_assign(self, value: int, value_len: int, ptr_addr: int):
        """
        Assigns a real value to an address that is stored in a ptr
        """
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("load", register(reg1), address(ptr_addr))
        self.write_format("iload", register(reg2), value)
        self.write_format(store_abs_of_len(value_len), register(reg1), register(reg2))

        self.manager.append_regs(reg2, reg1)

    def struct_attr(self, struct_addr, attr_pos, res_addr):
        reg1, reg2 = self.manager.require_regs(2)

        # print(struct_addr, res_addr)

        self.write_format("aload", register(reg1), number(struct_addr))
        self.write_format("iload", register(reg2), number(attr_pos))
        self.write_format("addi", register(reg1), register(reg2))
        self.write_format("iload", register(reg2), number(res_addr))
        self.write_format("store", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def call_named_function(self, fn_name: str, args: list, rtn_addr: int, ret_len: int):
        reg1, reg2 = self.manager.require_regs(2)

        self.set_call(args, reg1, reg2, ret_len, rtn_addr)
        self.write_format("call_fn", fn_name)

        self.manager.append_regs(reg2, reg1)

    def call_ptr_function(self, fn_ptr: int, args: list, rtn_addr: int, ret_len):
        reg1, reg2 = self.manager.require_regs(2)

        self.set_call(args, reg1, reg2, ret_len, rtn_addr)
        self.write_format("call", address(fn_ptr))

        self.manager.append_regs(reg2, reg1)

    def call_method(self, inst_ptr_addr, method_id, args: list, rtn_addr, rtn_len, offset):
        """
        :param inst_ptr_addr: the relative address that stores the pointer to instance
        :param method_id:
        :param args:
        :param rtn_addr:
        :param rtn_len:
        :param offset: the offset of class pointer in instance. Typically: __class__ = 0, super = INT_LEN
        :return:
        """
        reg1, reg2, reg3 = self.manager.require_regs(3)

        self.write_format("load", register(reg1), address(inst_ptr_addr))
        self.write_format("iload", register(reg2), number(method_id))
        self.write_format("iload", register(reg3), number(offset))
        self.write_format("get_method", register(reg1), register(reg2), register(reg3))
        self.set_call(args, reg2, reg3, rtn_len, rtn_addr)
        self.write_format("call_reg", register(reg1))

        self.manager.append_regs(reg3, reg2, reg1)

    def set_call(self, args: list, reg1, reg2, ret_len, rtn_addr):
        count = 0
        for arg in args:
            arg_addr = arg[0]
            arg_length = arg[1]
            self.write_format("aload_sp", register(reg1), address(count))
            if arg_length == 1:
                pass
            elif arg_length == util.INT_LEN:
                self.write_format("load", register(reg2), address(arg_addr))
                self.write_format("store_abs", register(reg1), register(reg2))
            elif arg_length == util.CHAR_LEN:
                self.write_format("loadc", register(reg2), address(arg_addr))
                self.write_format("store_abs", register(reg1), register(reg2))
            else:
                raise errs.TpaError("Unexpected arg length. ")

            count += arg_length

        # if ret_len == 1:
        #     pass
        # elif ret_len == util.CHAR_LEN:
        #     self.write_format("iload", register(reg1), number(rtn_addr))
        #     self.write_format("set_ret", register(reg1))
        # elif ret_len == util.INT_LEN:
        #     self.write_format("iload", register(reg1), number(rtn_addr))
        #     self.write_format("set_ret", register(reg1))
        # elif ret_len == util.FLOAT_LEN:
        if ret_len > 0:
            self.write_format("iload", register(reg1), number(rtn_addr))
            self.write_format("set_ret", register(reg1))
        # if void, do nothing

    def require_name(self, name: str, fn_ptr: int):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("require", name, address(fn_ptr), register(reg1), register(reg2))

        self.manager.append_regs(reg2, reg1)

    def invoke_ptr(self, fn_ptr: int, args: list, rtn_addr: int, ret_len: int):
        reg1, reg2 = self.manager.require_regs(2)

        self.set_call(args, reg1, reg2, ret_len, rtn_addr)
        self.write_format("invoke", address(fn_ptr))

        self.manager.append_regs(reg2, reg1)

    def if_zero_goto(self, cond_addr: int, label: str):
        reg1 = self.manager.require_reg()

        self.write_format("load", register(reg1), address(cond_addr))
        self.write_format("if_zero_goto", register(reg1), label)

        self.manager.append_regs(reg1)

    def write_format(self, *inst):
        self.output.append(self._format(*inst))

    @staticmethod
    def _format(*inst):
        mne = inst[0]
        s = "    " + mne
        s += " " * max(14 - len(mne), 1)
        for i in range(1, len(inst)):
            x = str(inst[i])
            s += x
            s += " " * max(8 - len(x), 1)
        return s.rstrip()

    def generate(self, main_file_path, main_has_arg=False):
        if self.is_global:
            self._global_generate(main_file_path, main_has_arg)
        else:
            self.local_generate()

    def _global_generate(self, main_file_path, main_has_arg):
        literal_str = " ".join([str(int(b)) for b in self.manager.literal])
        merged = ["bits", str(util.VM_BITS),
                  "stack_size", str(util.STACK_SIZE),
                  "global_length", str(self.manager.global_length()),
                  "literal", literal_str,
                  "classes"]

        for ct in self.manager.class_headers:
            ct: typ.ClassType
            full_name = util.class_name_with_path(ct.name, ct.file_path)
            line = "class " + full_name + " mro"
            for mro_t in ct.mro:
                line += " $" + str(mro_t.class_ptr)
            line += " methods"
            # print(ct.method_rank)
            for method_name, method_t in ct.method_rank:
                # for name in ct.methods:
                #     if name == method_name:
                line += " $" + str(ct.methods[method_name][method_t][1])
            merged.append(line)
        merged.append("")

        for fn_name in self.manager.functions_map:
            fo = self.manager.functions_map[fn_name]
            content = fo.compile()
            merged.extend(content)

        self.output = merged + self.output

        if main_has_arg:
            param_types = [typ.TYPE_STRING_ARR]
            self.write_format("main_arg")
        else:
            param_types = []
        self.write_format("aload", "%0", "$1")
        self.write_format("set_ret", "%0")
        self.write_format("call_fn",
                          util.name_with_path(typ.function_poly_name("main", param_types, False), main_file_path, None))
        self.write_format("exit")

    def local_generate(self):
        pass

    def result(self):
        return self.output
