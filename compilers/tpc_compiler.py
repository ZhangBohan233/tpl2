import sys
import compilers.util as util
import compilers.tokens_lib as tl
import compilers.errors as errs
import compilers.types as typ

SIGNATURE = "TPC_".encode()  # 84, 80, 67, 95

"""
Naming rule of instructions:
[pre] + inst + [type] + _[special description]

pre: aim for inst, for example, 'i' for instant, 'a' for address
type: 'i' for int, 'f' for float, 'c' for char, 'b' for byte
"""
INSTRUCTIONS = {
    "nop": (0,),
    "sleep": (1,),
    "load": (2, 1, util.INT_LEN),  # load   %reg  $rel_addr     | load value stored in $rel_addr to %reg
    "iload": (3, 1, util.INT_LEN),  # iload   %reg  value
    "aload": (4, 1, util.INT_LEN),  # aload   %reg  $rel_addr    | load the "address" relative to fp to reg
    "aload_sp": (5, 1, util.INT_LEN),  # aload_sp   %reg  $rel_addr    | load the "address" relative to sp to reg
    #                                  # these two instructions just do a conversion from relative addr to absolute addr
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
    "stop": (20,),
    "put_ret": (21, 1),  # put_ret    %reg    | put value from %reg to returning addr previously set
    "copy": (22, 1, 1),  # copy     %reg1   %reg2   | copy content in (abs_addr %reg2) to (abs_addr %reg1)
    "if_zero_jump": (23, 1, util.INT_LEN),
    "invoke": (24, util.INT_LEN),
    "rload_abs": (25, 1, 1),  # rload_abs   %reg1   %reg2   | load value with abs addr stored in %reg2 to %reg1
    #                         # 使用存储在%reg2内的绝对地址，将该地址的内存读入%reg1
    "addi": (30, 1, 1),
    "subi": (31, 1, 1),
    "muli": (32, 1, 1),
    "divi": (33, 1, 1),
    "modi": (34, 1, 1),
    "eqi": (35, 1, 1),
    "nei": (36, 1, 1),
    "gti": (37, 1, 1),
    "lti": (38, 1, 1),
    "gei": (39, 1, 1),
    "lei": (40, 1, 1),
    "negi": (41, 1),
    "not": (42, 1),
    "i_to_f": (60, 1),  # convert int in %reg to float, store in %reg
    "f_to_i": (61, 1),
}

MNEMONIC = {
    "fn", "entry", "call_fn", "label", "stop"
}

PSEUDO_INSTRUCTIONS = {
    "load_lit": (256, 1, util.INT_LEN),
}

STR_PSEUDO_INSTRUCTIONS = {
    "if_zero_goto": 257,
    "goto": 258
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
        # print(compiled)
        with open(out_name, "wb") as wf:
            wf.write(compiled)

    def compile_bytes(self):
        """
        Compiled 64 bits tpc structure:

        signature: 0 ~ 4

        # INFO HEADER
        vm_bits: 4 ~ 5
        extra_info: 5 ~ 16

        stack_size: 16 ~ @24
        global_length: @24 ~ @32
        literal_length: @32 ~ @40
        literal: @40 ~ (@40 + literal_length)
        functions: (@40 + literal_length) ~ end of functions
        function_assignments: end of functions ~ end of functions + (function count * length of assignment)
        entry: end of function_assignments ~ end - @8
        entry_len: (end - @8) ~ end

        Note that '@' marks this depends on vm bits

        :return:
        """
        vm_bits = 0
        literal_length = 0
        literal = bytearray()
        function_body_positions = {}
        function_pointers = {}
        function_list = []
        body = bytearray()  # body begins with index 'literal_length + global_length'
        cur_fn_body = []
        entry_part = None
        labels = {}
        jumps = {}
        goto_count = 0

        with open(self.tpc_file, "r") as rf:
            lines = [line.strip() for line in rf.readlines()]
            i = 0
            length = len(lines)
            while i < length:
                line = lines[i]
                lf = tl.LineFile(self.tpc_file, i + 1)
                if line == "bits":
                    vm_bits = int(lines[i + 1])
                    i += 1
                elif line == "stack_size":
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
                    if literal_length != 0 and len(literal) != literal_length:
                        raise errs.TpaError("Actual literal length does not match declared literal length.")
                    else:
                        literal_length = len(literal)
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
                            cur_fn_body = []
                            function_pointers[cur_fn_name] = cur_fn_ptr
                            function_list.append(cur_fn_name)
                            function_body_positions[cur_fn_name] = len(body)
                        elif inst == "entry":
                            cur_fn_body = []
                        elif inst == "call_fn":
                            fn_name = instructions[1]
                            fn_ptr = function_pointers[fn_name]
                            tup = INSTRUCTIONS["call"]
                            cur_fn_body.append(tup[0])
                            cur_fn_body.extend(util.int_to_bytes(fn_ptr))
                        elif inst == "label":
                            label_name = instructions[1]
                            labels[label_name] = len(cur_fn_body)
                        elif inst == "goto":
                            label_name = instructions[1]
                            cur_fn_body.append(STR_PSEUDO_INSTRUCTIONS["goto"])
                            cur_fn_body.extend(util.int_to_bytes(goto_count))
                            jumps[goto_count] = label_name
                            goto_count += 1
                        elif inst == "if_zero_goto":
                            label_name = instructions[2]
                            cur_fn_body.append(STR_PSEUDO_INSTRUCTIONS["if_zero_goto"])
                            cur_fn_body.append(num_single(inst, instructions[1], 1, lf))
                            cur_fn_body.extend(util.int_to_bytes(goto_count))
                            jumps[goto_count] = label_name
                            goto_count += 1
                        elif inst == "stop":  # end of a function, not a 'return'
                            compiled_fn_body = self.compile_function(cur_fn_body, labels, jumps)
                            body.extend(compiled_fn_body)
                            labels.clear()
                            jumps.clear()
                            goto_count = 0
                        elif inst == "require":
                            req_name = instructions[1]
                            req_ptr_addr = num_single("require", instructions[2], util.PTR_LEN, lf)
                            reg1 = instructions[3]
                            reg2 = instructions[4]
                            req_id, req_type = typ.NATIVE_FUNCTIONS[req_name]
                            # function_pointers[req_name] = req_ptr_addr

                            self.compile_inst("iload", ["iload", reg1, "$" + str(req_id)], cur_fn_body, lf)
                            self.compile_inst("iload", ["iload", reg2, "$" + str(req_ptr_addr)], cur_fn_body, lf)
                            self.compile_inst("store", ["store", reg2, reg1], cur_fn_body, lf)

                        elif inst in INSTRUCTIONS:
                            # real instructions
                            self.compile_inst(inst, instructions, cur_fn_body, lf)

                            if inst == "exit":  # end of program
                                entry_part = self.compile_function(cur_fn_body, labels, jumps)

                        elif inst in PSEUDO_INSTRUCTIONS:
                            self.compile_pseudo_inst(inst, instructions, cur_fn_body, lf)
                        else:
                            raise errs.TpaError("Unknown instruction {}. ".format(inst), lf)
                i += 1

        header = SIGNATURE + bytes((vm_bits,)) + util.empty_bytes(11) + \
                 util.int_to_bytes(self.stack_size) + util.int_to_bytes(self.global_length) + \
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

    def compile_function(self, body: iter, labels: dict, jumps: dict) -> bytearray:
        goto = STR_PSEUDO_INSTRUCTIONS["goto"]
        if_zero_goto = STR_PSEUDO_INSTRUCTIONS["if_zero_goto"]
        jump = INSTRUCTIONS["jump"]
        if_zero_jump = INSTRUCTIONS["if_zero_jump"]
        i = 0
        length = len(body)
        while i < length:
            b = body[i]
            if b == goto:
                goto_id = util.bytes_to_int(body[i + 1:i + 1 + util.INT_LEN])
                tar_label = jumps[goto_id]
                label_pos = labels[tar_label]
                end_len = i + util.INT_LEN + 1
                jump_len = label_pos - end_len
                body[i] = jump[0]
                body[i + 1: i + 1 + util.INT_LEN] = util.int_to_bytes(jump_len)
                i = end_len
            elif b == if_zero_goto:
                goto_id = util.bytes_to_int(body[i + 2:i + 2 + util.INT_LEN])
                tar_label = jumps[goto_id]
                label_pos = labels[tar_label]
                end_len = i + util.INT_LEN + 2
                jump_len = label_pos - end_len
                body[i] = if_zero_jump[0]
                body[i + 2: i + 2 + util.INT_LEN] = util.int_to_bytes(jump_len)
                i = end_len
            else:
                i += 1
        return bytearray(body)

    def compile_pseudo_inst(self, inst: str, instruction: iter, cur_fn_body: iter, lf: tl.LineFile):
        tup = PSEUDO_INSTRUCTIONS[inst]
        num_inst = inst_to_num(instruction, tup, lf)
        if inst == "load_lit":
            lit_start = self.stack_size + self.global_length
            self.compile_inst("load",
                              ["load", instruction[1], "$" + str(num_inst[2] + lit_start)],
                              cur_fn_body,
                              lf)

    def compile_inst(self, inst: str, instruction: list, cur_fn_body: iter, lf: tl.LineFile):
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
    :param lf: debug info: line and file
    :return: a new list contained numeric instruction, with a None at the first position to maintain the same length
    """
    lst = [None]
    for j in range(1, len(tup)):
        lst.append(num_single(actual_line[0], actual_line[j], tup[j], lf))
    return lst


def num_single(inst: str, symbol: str, expected_len: int, lf) -> int:
    if symbol.isdigit():
        if expected_len != util.INT_LEN:
            raise errs.TpaError("Instruction argument of {} length do not match. ".format(inst), lf)
        num = int(symbol)
    else:
        leading = symbol[0]
        if expected_len != LENGTHS[leading]:
            raise errs.TpaError("Instruction argument of {} length do not match. ".format(inst), lf)
        num = int(symbol[1:])
    return num


if __name__ == '__main__':
    if len(sys.argv) > 1:
        file = sys.argv[1]
        cmp = TpcCompiler(file)
        cmp.compile()
