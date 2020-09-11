import compilers.errors as errs
import compilers.util as util


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


class LabelManager:
    def __init__(self):
        self._else_count = 0
        self._endif_count = 0
        self._loop_title_count = 0
        self._end_loop_count = 0
        self._general_count = 0

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


class Manager:
    def __init__(self, literal: bytes):
        self.literal = literal
        self.blocks = []
        self.available_regs = [7, 6, 5, 4, 3, 2, 1, 0]
        self.gp = util.STACK_SIZE
        self.sp = util.INT_LEN + 1
        self.functions_map = {}
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

    def map_function(self, name: str, file_path, body: list):
        self.functions_map[util.name_with_path(name, file_path)] = body

    def global_length(self):
        return self.gp - util.STACK_SIZE


class TpaOutput:
    def __init__(self, manager: Manager, is_global=False):
        self.manager: Manager = manager
        self.is_global = is_global
        self.output = ["entry"] if is_global else []

    def add_function(self, name, file_path, fn_ptr):
        self.output.append("fn " + util.name_with_path(name, file_path) + " " + address(fn_ptr))
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

    def binary_arith(self, op_inst: str, left: int, right: int, res: int):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("load", register(reg1), address(left))
        self.write_format("load", register(reg2), address(right))
        self.write_format(op_inst, register(reg1), register(reg2))
        self.write_format("iload", register(reg2), number(res))
        self.write_format("store", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def binary_arith_i(self, op_inst: str, left: int, right_value: int, res: int):
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

    def take_addr(self, value_addr: int, res_addr: int):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("aload", register(reg1), address(value_addr))
        self.write_format("iload", register(reg2), number(res_addr))
        self.write_format("store", register(reg2), register(reg1))

        self.manager.append_regs(reg2, reg1)

    def value_in_addr_op(self, ptr_addr: int, res_addr: int):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("load", register(reg1), address(ptr_addr))
        self.write_format("rload_abs", register(reg2), register(reg1))
        self.write_format("iload", register(reg1), number(res_addr))
        self.write_format("store", register(reg1), register(reg2))

        self.manager.append_regs(reg2, reg1)

    def ptr_assign(self, value_addr: int, ptr_addr: int):
        reg1, reg2 = self.manager.require_regs(2)

        self.write_format("load", register(reg1), address(ptr_addr))
        self.write_format("load", register(reg2), address(value_addr))
        self.write_format("store_abs", register(reg1), register(reg2))

        self.manager.append_regs(reg2, reg1)

    def struct_attr(self, struct_addr, attr_pos, res_addr):
        reg1, reg2 = self.manager.require_regs(2)

        print(struct_addr, res_addr)

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

    def generate(self, main_file_path):
        if self.is_global:
            self._global_generate(main_file_path)
        else:
            self.local_generate()

    def _global_generate(self, main_file_path):
        literal_str = " ".join([str(int(b)) for b in self.manager.literal])
        merged = ["bits", str(util.VM_BITS),
                  "stack_size", str(util.STACK_SIZE),
                  "global_length", str(self.manager.global_length()),
                  "literal_length", str(len(self.manager.literal)),
                  "literal", literal_str,
                  ""]

        for fn_name in self.manager.functions_map:
            content = self.manager.functions_map[fn_name]
            merged.extend(content)

        self.output = merged + self.output

        self.write_format("aload", "%0", "$1")
        self.write_format("set_ret", "%0")
        self.write_format("call_fn", util.name_with_path("main", main_file_path))
        self.write_format("exit")

    def local_generate(self):
        pass

    def result(self):
        return self.output
