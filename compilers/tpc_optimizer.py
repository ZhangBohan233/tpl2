import compilers.tokens_lib as tl


class TpcOptimizer:
    def __init__(self, tpc_file: str, opt_level: int):
        self.tpc_file = tpc_file
        self.opt_level = opt_level

        self.opt_literal = opt_level >= 1
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

                if line == "bits":
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
                else:
                    instructions = \
                        [part for part in [part.strip() for part in line.split(" ")] if len(part) > 0]
                    if len(instructions) > 0:
                        inst = instructions[0]
                        if inst == "fn":
                            fn_name = instructions[1]
                            fn_ptr = instructions[2]
                            self.functions[fn_name] = (fn_ptr, cur_out)
                            self.function_orders.append(fn_name)
                        elif inst == "stop":
                            cur_out.append(instructions)
                            cur_out = []
                        elif inst == "entry":
                            cur_out = self.entry
                            cur_out.append(instructions)
                        else:
                            cur_out.append(instructions)
                i += 1

    def compile_to_list(self):
        body = []
        for fn_name in self.function_orders:
            fn_addr, fn_body = self.functions[fn_name]

            if self.opt_literal:
                self.optimize_literal(fn_body)

            body.append(f"\nfn {fn_name} {fn_addr}")
            for inst in fn_body:
                self.write_format(body, *inst)

        entry = ["\nentry"]
        for inst in self.entry:
            self.write_format(entry, *inst)
        return self.header + body + entry

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
