import compilers.tokens_lib as tl
import compilers.util as util


class TpcOptimizer:
    def __init__(self, tpc_file: str, opt_level: int):
        self.tpc_file = tpc_file
        self.opt_level = opt_level

        self.opt_literal = opt_level >= 1
        self.do_inline = opt_level >= 1
        self.retract_literal = opt_level >= 2

        self.bits = 0
        self.stack_size = 0
        self.global_length = 0

        self.header = []
        self.functions = {}
        self.function_orders = []
        self.entry = []

    def addr_is_literal(self, addr):
        return self.stack_size + self.global_length <= addr

    def optimize(self, out_name: str):
        self.read_instructions()

        out_list = self.compile_to_list()
        out_str = "\n".join(out_list)

        with open(out_name, "w") as wf:
            wf.write(out_str)

    def read_instructions(self):
        cur_out = []

        with open(self.tpc_file, "r") as rf:
            lines = [line.strip("\n") for line in rf.readlines()]
            i = 0
            length = len(lines)
            while i < length:
                orig_line = lines[i]
                line = orig_line.strip()
                lf = tl.LineFile(self.tpc_file, i + 1)

                if line == "version":
                    self.header.append(lines[i])
                    self.header.append(lines[i + 1])
                    i += 1
                elif line == "bits":
                    self.header.append(lines[i])
                    self.header.append(lines[i + 1])
                    self.bits = int(lines[i + 1])
                    i += 1
                elif line == "stack_size":
                    self.header.append(lines[i])
                    self.header.append(lines[i + 1])
                    self.stack_size = int(lines[i + 1])
                    i += 1
                elif line == "global_length":
                    self.header.append(lines[i])
                    self.header.append(lines[i + 1])
                    self.global_length = int(lines[i + 1])
                    i += 1
                elif line == "literal":
                    self.header.append(lines[i])
                    self.header.append(lines[i + 1])
                    i += 1
                elif line == "classes":
                    self.header.append(line)
                elif line.startswith("class "):
                    self.header.append(line)
                else:
                    instructions = \
                        [part for part in [part.strip() for part in line.split(" ")] if len(part) > 0]
                    if len(instructions) > 0:
                        inst = instructions[0]
                        if inst == "fn":
                            fn_name = instructions[1]
                            fn_ptr = instructions[2]
                            # need find by value to find ptr
                            self.functions[fn_name] = (fn_ptr, cur_out, "inline" in instructions[2:])
                            self.function_orders.append(fn_name)
                        elif inst == "stop":
                            cur_out.append(instructions)
                            cur_out = []
                        elif inst == "entry":
                            cur_out = self.entry
                            # cur_out.append(instructions)
                        else:
                            cur_out.append(instructions)
                i += 1

    def compile_to_list(self):
        body = []
        for fn_name in self.function_orders:
            fn_ptr, fn_body, inline = self.functions[fn_name]

            if self.opt_literal:
                self.optimize_literal(fn_body)
            if self.do_inline:
                fn_body = self.function_inline(fn_body, fn_ptr)

            body.append(f"\nfn {fn_name} {fn_ptr}")
            for inst in fn_body:
                self.write_format(body, *inst)

        entry = ["\nentry"]
        for inst in self.entry:
            self.write_format(entry, *inst)
        return self.header + body + entry

    def function_inline(self, fn_body: list, caller_ptr: str):
        occupied_regs = 0
        push_index = None
        pushed = None
        ret_addr = None
        new_body = []
        cur_args = []
        in_args = False
        for i in range(len(fn_body)):
            inst = fn_body[i]

            if inst[0] == "push":
                pushed = int(inst[1])
                push_index = i
            elif inst[0] == "set_ret":
                # [['iload', ra, aa], ['set_ret', ra]]
                ret_addr = fn_body[i - 1][2]
            elif inst[0] == "args":
                in_args = True
            elif inst[0] == "call":
                in_args = False
                args = cur_args.copy()
                cur_args.clear()

                called_ptr = inst[1]
                callee_ptr, callee_body, inline = self.find_func_at_ptr(called_ptr)
                # check this not a recursive call
                # this check does not guarantee the call is not recursive
                # i.e. cannot detect recursive call from 'getfunc'
                if callee_ptr != caller_ptr:
                    if inline:  # 'False' or 'None' are all excluded
                        # callee_body = self.function_inline(callee_body, callee_ptr)  # make callee inline first
                        inlined_body, more_push = \
                            self.get_inlined(callee_body, callee_ptr, args, ret_addr, pushed, occupied_regs)
                        if inlined_body is not None:
                            new_body.extend(inlined_body)
                            pushed += more_push
                            continue
                new_body.extend(args)

            if in_args:
                cur_args.append(inst)
            else:
                new_body.append(inst)
        new_body[push_index] = ["push", str(pushed)]
        return new_body

    def get_inlined(self, inline_func_body: list, inline_func_ptr: str, arg_inst: list,
                    ret_addr: str, caller_stack_occupy: int, occupied_regs):
        """
        Format of args:
        [['aload_sp', ra, aa],
         ['load<t>', rb, ab],
         ['store_abs', ra, rb], ...]

        :return:
        """
        args = {}
        args_len = 0
        # print(arg_inst)
        assert len(arg_inst) % 3 == 0  # first one is 'args', last two are iload and set_ret
        for ii in range(1, len(arg_inst) - 2, 3):
            dst_addr = arg_inst[ii][2]  # arg addr in the new function
            src_addr = arg_inst[ii + 1][2]  # arg original addr
            if arg_inst[ii + 1][0] == "loadb":
                arg_len = 1
            elif arg_inst[ii + 1][0] == "loadc":
                arg_len = util.CHAR_LEN
            else:
                arg_len = util.INT_LEN
            args[dst_addr] = src_addr, arg_len
            args_len += arg_len

        new_body = [["; begin of inlining " + inline_func_ptr]]
        # print(args)
        # print(inline_func_body)

        def make_addr(addr: str) -> str:
            if addr in args:
                return args[addr][0]
            elif int(addr[1:]) < stack_occupy:  # is in func stack
                return f"${int(addr[1:]) + caller_stack_occupy - args_len}"
            else:
                return addr

        ret_int = [["load", "ra", "aa"], ["put_ret", "ra"]]

        # a key to determine whether an addr is in the function's stack space:
        stack_occupy = None
        i = 0
        while i < len(inline_func_body):
            inst = inline_func_body[i]
            if inst[0] == "push":
                stack_occupy = int(inst[1])
            elif inst[0] == "push_fp" or inst[0] == "pull_fp" or inst[0] == "stop":
                # should be omitted
                pass
            elif inst[0] == "ret":
                # todo: if not at end of function, add a goto label
                pass
            elif matches(inline_func_body, i, ret_int):
                addr_to_return = make_addr(inst[2])
                # todo: register

                # see: tpa_producer.assign
                new_body.append(["load", "%0", addr_to_return])
                new_body.append(["iload", "%1", ret_addr])
                new_body.append(["store", "%1", "%0"])

                i += 1
            else:
                new_inst = []
                for item in inst:
                    item: str
                    if item.startswith("$"):
                        new_inst.append(make_addr(item))
                    else:
                        new_inst.append(item)
                new_body.append(new_inst)
            i += 1

        new_body.append(["; end of inlining"])
        return new_body, stack_occupy - args_len

    def find_func_at_ptr(self, ptr: str):
        for fn_name in self.functions:
            fn_ptr, fn_body, inline = self.functions[fn_name]
            if fn_ptr == ptr:
                return fn_ptr, fn_body, inline
        return None, None, None

    def optimize_literal(self, func_body: list):
        i = 0
        length = len(func_body)
        fmt = [["load", "ra", "aa"],
               ["iload", "rb", "ab"],
               ["store", "rb", "ra"]]
        lit_int_stacks = {}
        while i < length:
            if matches(func_body, i, fmt):
                lit_addr = int(func_body[i][2][1:])
                if self.addr_is_literal(lit_addr):
                    stack_addr = int(func_body[i + 1][2][1:])
                    lit_int_stacks[stack_addr] = lit_addr
                    i += 2
            i += 1
        # print(lit_int_stacks)

    def write_format(self, output: list, *inst):
        output.append(self._format(*inst))

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


def matches(tar_list: list, cur_index, fmt_list: list):
    """
    This method matches the given format

    Example:
    >>> lst = [["load", "%0", "$1048"], \
              ["iload", "%1", "$8"], \
              ["store", "%1", "%0"]]
    >>> fmt = [["load", "ra", "aa"], \
              ["iload", "rb", "ab"], \
              ["store", "rb", "ra"]]
    >>> matches(lst, 0, fmt)
    True

    :param tar_list:
    :param cur_index:
    :param fmt_list:
    :return:
    """
    if cur_index + len(fmt_list) > len(tar_list):
        return False
    patterns = {}
    for i in range(len(fmt_list)):
        tar = tar_list[i + cur_index]
        fmt = fmt_list[i]
        if len(tar) != len(fmt):
            return False
        for j in range(len(fmt)):
            pat = fmt[j]
            src = tar[j]
            if pat != src:
                if pat in patterns:
                    if patterns[pat] != src:
                        return False
                else:
                    patterns[pat] = src
    return True


if __name__ == '__main__':
    lst_test = [["load", "%0", "$1048"],
                ["iload", "%1", "$8"],
                ["store", "%1", "%0"]]
    fmt_test = [["load", "ra", "aa"],
                ["iload", "rb", "ab"],
                ["store", "rb", "ra"]]
    print(matches(lst_test, 0, fmt_test))
