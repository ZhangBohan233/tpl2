import compilers.tokens_lib as tl


class TpcOptimizer:
    def __init__(self, tpc_file: str, opt_level: int):
        self.tpc_file = tpc_file
        self.opt_level = opt_level

        self.bits = 0
        self.stack_size = 0
        self.global_length = 0

        self.header = []
        self.functions = {}
        self.function_orders = []
        self.entry = []

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
            body.append(f"\nfn {fn_name} {fn_addr}")
            for inst in fn_body:
                self.write_format(body, *inst)

        entry = ["\nentry"]
        for inst in self.entry:
            self.write_format(entry, *inst)
        return self.header + body + entry

    def matches(self):
        pass

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
