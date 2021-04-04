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
    "load": (2, 1, util.INT_PTR_LEN),  # load   %reg  $rel_addr     | load value stored in $rel_addr to %reg
    "iload": (3, 1, util.INT_PTR_LEN),  # iload   %reg  value
    "aload": (4, 1, util.INT_PTR_LEN),  # aload   %reg  $rel_addr    | load the "address" relative to fp to reg
    "aload_sp": (5, 1, util.INT_PTR_LEN),  # aload_sp   %reg  $rel_addr    | load the "address" relative to sp to reg
    #                                  # these two instructions just do a conversion from relative addr to absolute addr
    "store": (6, 1, 1),  # store   %reg1   %reg2    | store value in %reg2 to rel_addr in %reg1
    "astore": (7, 1, 1),  # astore   %reg1   %reg2    | converts value in %reg2 to abs addr
    #                                  # then store to rel_addr in %reg1
    "astore_sp": (8,),
    "store_abs": (9, 1, 1),  # store_abs   %reg1   %reg2    | store value in %reg2 to abs_addr in %reg1
    "jump": (10, util.INT_PTR_LEN),
    "move": (11,),
    "push": (12, util.INT_PTR_LEN),
    "ret": (13,),
    "push_fp": (14,),
    "pull_fp": (15,),
    "set_ret": (16, 1),  # set_ret    %reg   | set the return abs addr in %reg to ret_stack
    "call": (17, util.INT_PTR_LEN),  # | call function at addr
    "exit": (18,),
    "true_addr": (19, 1),  # true_addr   %reg    | relative addr to absolute addr
    "stop": (20,),
    "put_ret": (21, 1),  # put_ret    %reg    | put value from %reg to returning addr previously set
    "copy": (22, 1, 1),  # copy     %reg1   %reg2   | copy content in (abs_addr %reg2) to (abs_addr %reg1)
    "if_zero_jump": (23, 1, util.INT_PTR_LEN),
    "invoke": (24, util.INT_PTR_LEN),
    "rload_abs": (25, 1, 1),  # rload_abs   %reg1   %reg2   | load value with abs addr stored in %reg2 to %reg1
    #                         # 使用存储在%reg2内的绝对地址，将该地址的内存读入%reg1
    "rloadc_abs": (26, 1, 1),
    "rloadb_abs": (27, 1, 1),
    "call_reg": (28, 1),  # %reg fn_addr
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
    "lshift": (43, 1, 1),
    "rshift": (44, 1, 1),  # arithmetic right shift, fill the first bit
    "rshiftl": (45, 1, 1),  # logical right shift, fill 0
    "and": (46, 1, 1),  # bitwise and
    "or": (47, 1, 1),  # bitwise of
    "xor": (48, 1, 1),  # bitwise xor
    "addf": (50, 1, 1),
    "subf": (51, 1, 1),
    "mulf": (52, 1, 1),
    "divf": (53, 1, 1),
    "modf": (54, 1, 1),
    "eqf": (55, 1, 1),
    "nef": (56, 1, 1),
    "gtf": (57, 1, 1),
    "ltf": (58, 1, 1),
    "gef": (59, 1, 1),
    "lef": (60, 1, 1),
    "negf": (61, 1),
    "i_to_f": (65, 1),  # convert int in %reg to float, store in %reg
    "f_to_i": (66, 1),
    "loadc": (70, 1, util.INT_PTR_LEN),
    "storec": (71, 1, 1),
    "storec_abs": (72, 1, 1),
    "main_arg": (79,),
    "loadb": (80, 1, util.INT_PTR_LEN),
    "storeb": (81, 1, 1),
    "storeb_abs": (82, 1, 1),
    "get_method": (83, 1, 1, 1),  # %reg1 inst_ptr_addr  %reg2 method_id  %reg3 backup   |
    #                             # get method ptr of a class, store to %reg1
    "subclass": (84, 1, 1, 1, 1),  # %reg1 parent_class   %reg2 child_class   %reg3 temp1   %reg4 temp2
    #                               # | store true to %reg1
    #                               # if parent_class is super of child_class
    "exitv": (85, 1),  # exitv   %reg1 value    | exit with value stored in %reg1
    "rt_type": (86, 1, 1),  # rt_type   %reg1 dst_addr   %reg2 src_addr    | runtime type
    "field_type": (87, 1, 1, 1),  # field_type   %reg1 dst_addr   %reg2 class_ptr   %reg3 field_pos
}

MNEMONIC = {
    "fn", "entry", "call_fn", "invoke_fn", "label", "stop", "args"
}

PSEUDO_INSTRUCTIONS = {
    "load_lit": (256, 1, util.INT_PTR_LEN),
    "loadc_lit": (257, 1, util.INT_PTR_LEN),
    "loadb_lit": (258, 1, util.INT_PTR_LEN),
    "lit_abs": (259, 1, util.INT_PTR_LEN),  # convert the lit_pos to addr
}

STR_PSEUDO_INSTRUCTIONS = {
    "if_zero_goto": 257,
    "goto": 258
}

LENGTHS = {
    "%": 1,
    "$": util.INT_PTR_LEN
}


class TpeCompiler:
    def __init__(self, tpc_file: str):
        self.tpc_file = tpc_file

        self.stack_size = 0
        self.global_length = 0

    def compile(self, out_name=None):
        if out_name is None:
            out_name = util.replace_extension(self.tpc_file, "tpe")

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
        bytecode_version: 5 ~ 7
        extra_info: 7 ~ 16

        stack_size: 16 ~ @24
        global_length: @24 ~ @32
        literal_length: @32 ~ @40
        class_literal_length: @40 ~ @48
        class_header_length: @48 ~ @56
        literal: @56 ~ (@56 + literal_length)
        class_literals: (@56 + literal_length) ~ (@56 + literal_length + class_literal_length)
        class_headers: (@56 + literal_length + class_literal_length) ~
                        (@56 + literal_length + class_header_length + class_literal_length)
        functions: (@56 + literal_length + class_header_length + class_literal_length) ~ end of functions
        class_assignments: end of functions ~ (end of functions + class count * length of assignment)
        function_assignments: end of class_assignments ~
            end of class_assignments + (function count * length of assignment)
        entry: end of function_assignments ~ end - @8
        entry_len: (end - @8) ~ end

        Note that '@' marks this depends on vm bits

        :return:
        """
        version = 0
        vm_bits = 0
        literal = bytearray()
        class_literal = bytearray()
        function_body_positions = {}
        function_pointers = {}
        function_list = []
        # class_header_lengths = {}
        class_pointers = {}
        class_list = []
        class_bodies = bytearray()
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
                if line == "version":
                    version = int(lines[i + 1])
                    i += 1
                elif line == "bits":
                    vm_bits = int(lines[i + 1])
                    i += 1
                elif line == "stack_size":
                    self.stack_size = int(lines[i + 1])
                    i += 1
                elif line == "global_length":
                    self.global_length = int(lines[i + 1])
                    i += 1
                elif line == "literal":
                    literal_str = lines[i + 1].split(" ")
                    for lit in literal_str:
                        literal.append(int(lit))
                    i += 1
                elif line == "classes":
                    pass
                elif line == "class_literals":
                    i += 1
                    cl_line = lines[i]
                    while cl_line != "end_class_literals":
                        lit_line = cl_line.split(" ")
                        for lit in lit_line:
                            class_literal.append(int(lit))
                        i += 1
                        cl_line = lines[i]
                elif line.startswith("class "):
                    # format of class header:
                    # Example in 64 bits
                    # 0 ~ 8: class_name pointer
                    # 8 ~ 16: mro array pointer
                    # 16 ~ 24: aligned_fields array pointer
                    # 24 ~ 32: method array pointer
                    content = [part for part in [part.strip() for part in line.split(" ")] if len(part) > 0]
                    class_name = content[1]
                    name_index = content.index("name") + 1
                    addr_index = content.index("addr") + 1
                    mro_index = content.index("mro") + 1
                    aligned_fields_index = content.index("aligned_fields") + 1
                    method_index = content.index("methods") + 1
                    class_header = util.int_to_bytes(int(content[name_index][1:])) + \
                                   util.int_to_bytes(int(content[mro_index][1:])) + \
                                   util.int_to_bytes(int(content[aligned_fields_index][1:])) + \
                                   util.int_to_bytes(int(content[method_index][1:]))

                    class_ptr = int(content[addr_index][1:])

                    class_list.append(class_name)  # name
                    class_pointers[class_name] = class_ptr
                    # class_header_lengths[class_name] = len(class_header)
                    class_bodies.extend(class_header)
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
                        elif inst == "args":
                            pass
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
                            req_ptr_addr = num_single("require", instructions[2], util.INT_PTR_LEN, lf)
                            reg1 = instructions[3]
                            reg2 = instructions[4]
                            req_id, req_type = typ.NATIVE_FUNCTIONS[req_name]
                            # native_pointers[req_name] = req_ptr_addr

                            self.compile_inst("iload", ["iload", reg1, "$" + str(req_id)], cur_fn_body, lf)
                            self.compile_inst("iload", ["iload", reg2, "$" + str(req_ptr_addr)], cur_fn_body, lf)
                            self.compile_inst("store", ["store", reg2, reg1], cur_fn_body, lf)

                        elif inst in INSTRUCTIONS:
                            # real instructions
                            self.compile_inst(inst, instructions, cur_fn_body, lf)

                            if inst == "exit":  # end of program
                                entry_part = self.compile_function(cur_fn_body, labels, jumps)

                        else:
                            raise errs.TpaError("Unknown instruction {}. ".format(inst), lf)
                i += 1

        header = SIGNATURE + bytes((vm_bits,)) + \
                 util.u_short_to_bytes(version) + util.empty_bytes(9) + \
                 util.int_to_bytes(self.stack_size) + \
                 util.int_to_bytes(self.global_length) + \
                 util.int_to_bytes(len(literal)) + \
                 util.int_to_bytes(len(class_literal)) + \
                 util.int_to_bytes(len(class_bodies)) + \
                 literal + \
                 class_literal + \
                 class_bodies
        # print(class_header_lengths)
        entry_lf = tl.LineFile("tpa compiler ", 0)
        # assigns value to all class pointers
        all_len_before_classes = self.stack_size + self.global_length + len(literal) + len(class_literal)
        class_assignments = bytearray()
        class_pos = all_len_before_classes
        for class_name in class_list:
            class_ptr = class_pointers[class_name]
            self.compile_inst("iload", ["iload", "%0", "$" + str(class_pos)], class_assignments, entry_lf)
            self.compile_inst("iload", ["iload", "%1", "$" + str(class_ptr)], class_assignments, entry_lf)
            self.compile_inst("store", ["store", "%1", "%0"], class_assignments, entry_lf)
            class_pos += util.INT_PTR_LEN * 4  # header length

        fn_assignments = bytearray()
        all_len_before_real_fn = all_len_before_classes + len(class_bodies)
        for name in function_list:
            pos = function_body_positions[name]
            fn_ptr = function_pointers[name]
            fn_real_pos = all_len_before_real_fn + pos
            self.compile_inst("iload", ["iload", "%0", "$" + str(fn_real_pos)], fn_assignments, entry_lf)
            self.compile_inst("iload", ["iload", "%1", "$" + str(fn_ptr)], fn_assignments, entry_lf)
            self.compile_inst("store", ["store", "%1", "%0"], fn_assignments, entry_lf)

        entry_len = len(entry_part) + len(class_assignments) + len(fn_assignments)
        return header + body + class_assignments + fn_assignments + entry_part + util.int_to_bytes(entry_len)

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
                goto_id = util.bytes_to_int(body[i + 1:i + 1 + util.INT_PTR_LEN])
                tar_label = jumps[goto_id]
                label_pos = labels[tar_label]
                end_len = i + util.INT_PTR_LEN + 1
                jump_len = label_pos - end_len
                body[i] = jump[0]
                body[i + 1: i + 1 + util.INT_PTR_LEN] = util.int_to_bytes(jump_len)
                i = end_len
            elif b == if_zero_goto:
                goto_id = util.bytes_to_int(body[i + 2:i + 2 + util.INT_PTR_LEN])
                tar_label = jumps[goto_id]
                label_pos = labels[tar_label]
                end_len = i + util.INT_PTR_LEN + 2
                jump_len = label_pos - end_len
                body[i] = if_zero_jump[0]
                body[i + 2: i + 2 + util.INT_PTR_LEN] = util.int_to_bytes(jump_len)
                i = end_len
            else:
                i += 1
        return bytearray(body)

    def compile_inst(self, inst: str, instruction: list, cur_fn_body: iter, lf: tl.LineFile):
        tup = INSTRUCTIONS[inst]
        num_inst = inst_to_num(instruction, tup, lf)

        cur_fn_body.append(tup[0])
        for j in range(1, len(tup)):
            num = num_inst[j]
            byte_len = tup[j]

            if byte_len == 1:
                cur_fn_body.append(num)
            elif byte_len == util.INT_PTR_LEN:
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
        if expected_len != util.INT_PTR_LEN:
            raise errs.TpaError("Instruction argument of {} length do not match. ".format(inst), lf)
        num = int(symbol)
    else:
        leading = symbol[0]
        if expected_len != LENGTHS[leading]:
            raise errs.TpaError("Instruction argument of {} length do not match. ".format(inst), lf)
        num = int(symbol[1:])
    return num
