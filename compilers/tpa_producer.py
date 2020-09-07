import compilers.errors as errs
import compilers.util as util


STACK_SIZE = 1024


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


class Manager:
    def __init__(self, literal: bytes):
        self.literal = literal
        self.blocks = []
        self.available_regs = [7, 6, 5, 4, 3, 2, 1, 0]
        self.gp = STACK_SIZE
        self.sp = util.INT_LEN + 1
        self.functions_map = {}

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

    def map_function(self, ptr: int, name: str, body: list):
        self.functions_map[name] = (ptr, body)

    def global_length(self):
        return self.gp - STACK_SIZE


class TpaOutput:
    def __init__(self, manager: Manager, is_global=False):
        self.manager: Manager = manager
        self.is_global = is_global
        self.output = ["entry"] if is_global else []

    def add_function(self, name, fn_ptr):
        self.output.append("fn " + name + " " + address(fn_ptr))
        self.write_format("push_fp")

    def add_indefinite_push(self) -> int:
        self.output.append("push")
        return len(self.output) - 1

    def modify_indefinite_push(self, index, length):
        push = self.format("push", length)
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

    def return_value(self, src_addr):
        reg1 = self.manager.require_reg()

        self.write_format("load", register(reg1), address(src_addr))
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

    def call_named_function(self, fn_name: str, args: list, rtn_addr: int):
        reg1, reg2 = self.manager.require_regs(2)

        count = 0
        for arg in args:
            arg_addr = arg[0]
            arg_length = arg[1]
            self.write_format("aload_sp", register(reg1), address(count))
            if arg_length == util.INT_LEN:
                self.write_format("load", register(reg2), address(arg_addr))
                self.write_format("store_abs", register(reg1), register(reg2))

            count += arg_length

        self.write_format("iload", register(reg1), number(rtn_addr))
        self.write_format("set_ret", register(reg1))
        self.write_format("call_fn", fn_name)

        self.manager.append_regs(reg2, reg1)

    def call_ptr_function(self, fn_ptr: int, args: list, rtn_addr: int):
        reg1, reg2 = self.manager.require_regs(2)

        count = 0
        for arg in args:
            arg_addr = arg[0]
            arg_length = arg[1]
            self.write_format("aload_sp", register(reg1), address(count))
            if arg_length == util.INT_LEN:
                self.write_format("load", register(reg2), address(arg_addr))
                self.write_format("store_abs", register(reg1), register(reg2))

            count += arg_length

        self.write_format("iload", register(reg1), number(rtn_addr))
        self.write_format("set_ret", register(reg1))
        self.write_format("call", address(fn_ptr))

        self.manager.append_regs(reg2, reg1)

    def write_format(self, *inst):
        self.output.append(self.format(*inst))

    @staticmethod
    def format(*inst):
        mne = inst[0]
        s = "    " + mne
        s += " " * (14 - len(mne))
        for i in range(1, len(inst)):
            x = str(inst[i])
            s += x
            s += " " * (8 - len(x))
        return s.rstrip()

    def generate(self):
        if self.is_global:
            self._global_generate()
        else:
            self._local_generate()

    def _global_generate(self):
        literal_str = " ".join([str(int(b)) for b in self.manager.literal])
        merged = ["bits", str(util.VM_BITS),
                  "stack_size", str(STACK_SIZE),
                  "global_length", str(self.manager.global_length()),
                  "literal_length", str(len(self.manager.literal)),
                  "literal", literal_str,
                  ""]

        for fn_name in self.manager.functions_map:
            content = self.manager.functions_map[fn_name]
            merged.extend(content[1])

        self.output = merged + self.output

        self.write_format("aload", "%0", "$1")
        self.write_format("set_ret", "%0")
        self.write_format("call_fn", "main")
        self.write_format("exit")

    def _local_generate(self):
        pass

    def result(self):
        return self.output
