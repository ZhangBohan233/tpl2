import sys
import compilers.util as util
import compilers.tokens_lib as tl
import compilers.errors as errs

INSTRUCTIONS = {
    "nop": (0,),
    "sleep": (1,),
    "load": (2, 1, util.INT_LEN),  # load   %reg  $rel_addr     | load value stored in $rel_addr to %reg
    "iload": (3, 1, util.INT_LEN),  # iload   %reg  value
    "aload": (4, 1, util.INT_LEN),  # aload   %reg  $rel_addr    | load the "address" relative to fp to reg
    "aload_sp": (5, 1, util.INT_LEN),  # aload_sp   %reg  $rel_addr    | load the "address" relative to sp to reg
                                       # these two instructions just do a conversion from relative addr to absolute addr
    "store": (6, 1, 1),  # store   %reg1   %reg2    | store value in %reg2 to rel_addr in %reg1
    "astore": (7, 1),
    "astore_sp": (8,),
    "store_abs": (9, 1, 1),  # store_abs   %reg1   %reg2    | store value in %reg2 to abs_addr in %reg1
    "jump": (10, util.INT_LEN),
    "move": (11,),
    "push": (12, util.INT_LEN),
    "ret": (13,),
    "push_fp": (14,),
    "pull_fp": (15,),
    "set_ret": (16, 1),  # set_ret    %reg   | set the return abs addr in %reg to ret_stack
    "call": (17, util.INT_LEN),
    "exit": (18,),
    "true_addr": (19, 1),  # true_addr   %reg    | relative addr to absolute addr
    "put_ret": (21, 1),  # put_ret    %reg    | put value from %reg to returning addr previously set
    "copy": (22, 1, 1),  # copy     %reg1   %reg2   | copy content in (abs_addr %reg2) to (abs_addr %reg1)
    "addi": (30, 1, 1),
    "subi": (31, 1, 1),
    "muli": (32, 1, 1),
    "divi": (33, 1, 1),
    "modi": (34, 1, 1),
}

MNEMONIC = {
    "fn", "entry", "call_fn", "label"
}

PSEUDO_INSTRUCTIONS = {
    "load_lit": (0, 1, util.INT_LEN)
}

LENGTHS = {
    "%": 1,
    "$": util.INT_LEN
}


class TpcCompiler:
    def __init__(self, tpc_file: str):
        self.tpc_file = tpc_file

        self.stack_size = 1024
        self.global_length = 0

    def compile(self, out_name=None):
        if out_name is None:
            out_name = util.replace_extension(self.tpc_file, "tpc")

        compiled = self.compile_bytes()
        print(compiled)
        with open(out_name, "wb") as wf:
            wf.write(compiled)

    def compile_bytes(self):
        """
        Compiled tpc structure:

        stack_size: 0 ~ 8
        global_length: 8 ~ 16
        literal_length: 16 ~ 24
        literal: 24 ~ (24 + literal_length)
        functions: (24 + literal_length) ~ end of functions
        function_assignments: end of functions ~ end of functions + (function count * length of assignment)
        entry: end of function_assignments ~ end - 8
        entry_len: end - 8 ~ end

        :return:
        """
        literal_length = 0
        literal = bytearray()
        function_body_positions = {}
        function_pointers = {}
        function_list = []
        body = bytearray()  # body begins with index 'literal_length + global_length'
        cur_fn_body = bytearray()
        entry_part = None

        with open(self.tpc_file, "r") as rf:
            lines = [line.strip() for line in rf.readlines()]
            i = 0
            length = len(lines)
            while i < length:
                line = lines[i]
                lf = tl.LineFile(self.tpc_file, i + 1)
                if line == "stack_size":
                    self.stack_size = int(lines[i + 1])
                    i += 1
                elif line == "literal_length":
                    literal_length = int(lines[i + 1])
                    i += 1
                elif line == "global_length":
                    self.global_length = int(lines[i + 1])
                    i += 1
                elif line == "literal":
                    literal_str = lines[i + 1].split(" ")
                    for lit in literal_str:
                        literal.append(int(lit))
                    if len(literal) != literal_length:
                        raise errs.TpaError("Actual literal length does not match declared literal length.")
                    i += 1
                else:
                    instructions = \
                        [part for part in [part.strip() for part in line.split(" ")] if len(part) > 0]
                    for j in range(len(instructions)):
                        part = instructions[j]
                        if part == ";" or part.startswith(";", 0, -1):
                            instructions = instructions[:j]
                            break
                    if len(instructions) > 0:
                        inst = instructions[0]
                        if inst == "fn":
                            cur_fn_name = instructions[1]
                            if not instructions[2].startswith("$"):
                                raise errs.TpaError("Incorrect number format. ", lf)
                            cur_fn_ptr = int(instructions[2][1:])
                            cur_fn_body = bytearray()
                            function_pointers[cur_fn_name] = cur_fn_ptr
                            function_list.append(cur_fn_name)
                            function_body_positions[cur_fn_name] = len(body)
                        elif inst == "entry":
                            cur_fn_body = bytearray()
                        elif inst == "call_fn":
                            fn_name = instructions[1]
                            fn_ptr = function_pointers[fn_name]
                            tup = INSTRUCTIONS["call"]
                            cur_fn_body.append(tup[0])
                            cur_fn_body.extend(util.int_to_bytes(fn_ptr))
                        elif inst == "label":
                            pass
                        elif inst in INSTRUCTIONS:
                            # real instructions
                            self.compile_inst(inst, instructions, cur_fn_body, lf)

                            if inst == "ret":
                                compiled_fn_body = self.compile_function(cur_fn_body)
                                body.extend(compiled_fn_body)
                            elif inst == "exit":
                                entry_part = self.compile_function(cur_fn_body)

                        elif inst in PSEUDO_INSTRUCTIONS:
                            self.compile_pseudo_inst(inst, instructions, cur_fn_body, lf)
                        else:
                            raise errs.TpaError("Unknown instruction {}. ".format(inst), lf)
                i += 1

        header = util.int_to_bytes(self.stack_size) + util.int_to_bytes(self.global_length) + \
                 util.int_to_bytes(literal_length) + literal

        fn_assignments = bytearray()
        all_len_before_real_fn = self.stack_size + self.global_length + literal_length
        entry_lf = tl.LineFile("tpa compiler ", 0)
        for name in function_list:
            pos = function_body_positions[name]
            fn_ptr = function_pointers[name]
            fn_real_pos = all_len_before_real_fn + pos
            self.compile_inst("iload", ["iload", "%0", "$" + str(fn_real_pos)], fn_assignments, entry_lf)
            self.compile_inst("iload", ["iload", "%1", "$" + str(fn_ptr)], fn_assignments, entry_lf)
            self.compile_inst("store", ["store", "%1", "%0"], fn_assignments, entry_lf)

        entry_len = len(entry_part) + len(fn_assignments)
        return header + body + fn_assignments + entry_part + util.int_to_bytes(entry_len)

    def compile_function(self, body: bytearray) -> bytearray:
        return body.copy()

    def compile_pseudo_inst(self, inst: str, instruction: list, cur_fn_body: bytearray, lf: tl.LineFile):
        tup = PSEUDO_INSTRUCTIONS[inst]
        num_inst = inst_to_num(instruction, tup, lf)
        if inst == "load_lit":
            lit_start = self.stack_size + self.global_length
            self.compile_inst("load",
                              ["load", instruction[1], "$" + str(num_inst[2] + lit_start)],
                              cur_fn_body,
                              lf)

    def compile_inst(self, inst: str, instruction: list, cur_fn_body: bytearray, lf: tl.LineFile):
        tup = INSTRUCTIONS[inst]
        num_inst = inst_to_num(instruction, tup, lf)

        cur_fn_body.append(tup[0])
        for j in range(1, len(tup)):
            num = num_inst[j]
            byte_len = tup[j]

            if byte_len == 1:
                cur_fn_body.append(num)
            elif byte_len == util.INT_LEN:
                cur_fn_body.extend(util.int_to_bytes(num))

        if len(instruction) != len(tup):
            raise errs.TpaError("Instruction length error", lf)


def inst_to_num(actual_line: list, tup: tuple, lf) -> list:
    """
    Convert an instruction line to actual numbers

    :param actual_line: the actual instruction line, with str inst head at first
    :param tup: the designated instruction
    :param lf:
    :return: a new list contained numeric instruction, with a None at the first position to maintain the same length
    """
    lst = [None]
    for j in range(1, len(tup)):
        byte_len = tup[j]
        sym = actual_line[j]
        if sym.isdigit():
            if byte_len != util.INT_LEN:
                raise errs.TpaError("Instruction argument of {} length do not match. ".format(actual_line[0]), lf)
            num = int(sym)
        else:
            leading = sym[0]
            if byte_len != LENGTHS[leading]:
                raise errs.TpaError("Instruction argument of {} length do not match. ".format(actual_line[0]), lf)
            num = int(sym[1:])
        lst.append(num)
    return lst


if __name__ == '__main__':
    if len(sys.argv) > 1:
        file = sys.argv[1]
        cmp = TpcCompiler(file)
        cmp.compile()
