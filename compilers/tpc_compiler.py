import os
import compilers.util as util
import compilers.tokens_lib as tl
import compilers.errors as errs
import compilers.tpe_compiler as tpe


class TpcCompiler:
    """
    This class takes a tpa file and compile it to a tpc file.

    Which compiles all pseudo instructions to real instructions, and produces function list
    """

    def __init__(self, tpa_file: str):
        self.tpa_file = tpa_file

        self.stack_size = 0
        self.global_length = 0
        self.version = 0

    def compile(self, out_name=None):
        if out_name is None:
            out_name = util.replace_extension(self.tpa_file, "tpc")

        out_list = self.compile_to_list()

        out_str = "\n".join(out_list)

        with open(out_name, "w") as wf:
            wf.write(out_str)

    def compile_to_list(self):
        literal = []
        header_out = []
        body_out = []
        entry_out = []
        class_header_out = []
        class_literals = []  # list of (int, bytes), each represents a class and its ending pos
        cur_out = header_out

        function_pointers = {}  # full poly name: $addr_text
        native_pointers = {}
        class_pointers = {}  # full poly name: $addr_text

        string_class_addr = 0

        with open(self.tpa_file, "r") as rf:
            lines = [line.strip("\n") for line in rf.readlines()]
        for line in lines:
            line = line.strip()
            if line.startswith("fn "):
                first_line = list(filter(lambda l: len(l) > 0, [part.strip() for part in line.split(" ")]))
                name = first_line[1]
                addr = first_line[2]
                function_pointers[name] = addr
            elif line.startswith("require "):
                first_line = list(filter(lambda l: len(l) > 0, [part.strip() for part in line.split(" ")]))
                name = first_line[1]
                addr = first_line[2]
                native_pointers[name] = addr
            elif line.startswith("class "):
                first_line = list(filter(lambda l: len(l) > 0, [part.strip() for part in line.split(" ")]))
                name = first_line[1]
                addr = first_line[2]
                class_pointers[name] = addr
                if name.endswith(f"lib{os.sep}lang.tp$String"):
                    string_class_addr = int(addr[1:])

        i = 0
        length = len(lines)
        while i < length:
            orig_line = lines[i]
            line = orig_line.strip()
            lf = tl.LineFile(self.tpa_file, i + 1)

            if line == "version":
                cur_out.append(lines[i])
                cur_out.append(lines[i + 1])
                self.version = int(lines[i + 1])
                i += 1
            elif line == "stack_size":
                cur_out.append(lines[i])
                cur_out.append(lines[i + 1])
                self.stack_size = int(lines[i + 1])
                i += 1
            elif line == "global_length":
                cur_out.append(lines[i])
                cur_out.append(lines[i + 1])
                self.global_length = int(lines[i + 1])
                i += 1
            elif line == "literal":
                cur_out.append(lines[i])
                cur_out.append(lines[i + 1])
                literal_str = lines[i + 1].split(" ")
                for lit in literal_str:
                    literal.append(int(lit))
                i += 1
            elif line == "classes":
                cur_out = class_header_out
                cur_out.append("classes")
            elif line.strip().startswith("class "):
                class_parts = [part.strip() for part in line.split(" ")]
                class_name = class_parts[1]
                class_ptr = class_parts[2]

                i += 1
                new_line = lines[i].strip()
                while not new_line.endswith("endclass"):
                    class_parts.extend([part.strip() for part in new_line.split(" ")])
                    i += 1
                    new_line = lines[i].strip()
                i += 1  # skips 'endclass'
                mro_index = class_parts.index("mro")
                fields_index = class_parts.index("aligned_fields")
                methods_index = class_parts.index("methods")

                # make class literals

                # after stack, global, literal
                if len(class_literals) == 0:
                    classes_before = 0
                else:
                    classes_before = class_literals[-1][0]
                len_before = util.STACK_SIZE + self.global_length + len(literal) + classes_before
                this_class_lit = bytearray()
                class_name_ptr = len_before + len(this_class_lit)
                # print(class_name_ptr)
                class_name_chars = util.string_to_chars_bytes(class_name)
                class_name_str = util.make_string_header(util.int_to_bytes(string_class_addr), class_name_ptr) + \
                                 class_name_chars
                this_class_lit.extend(class_name_str)

                # mro array
                mro_arr_ptr = len_before + len(this_class_lit)
                mro_list = [int(class_ptr[1:])]  # first is class itself

                for mro_class in class_parts[mro_index + 1: fields_index]:
                    mro_ptr = class_pointers[mro_class]
                    mro_list.append(int(mro_ptr[1:]))

                mro_array = bytearray(util.make_array_header(len(mro_list), util.INT_CODE))
                for mro in mro_list:
                    mro_array.extend(util.int_to_bytes(mro))
                this_class_lit.extend(mro_array)

                # aligned fields array
                af_arr_ptr = len_before + len(this_class_lit)
                af_list = []

                fields_sublist = class_parts[fields_index + 1: methods_index]
                if len(fields_sublist) % 3 != 0:
                    raise errs.TpaError("Unexpected fields syntax. ", lf)
                for j in range(0, len(fields_sublist), 3):
                    field_name, field_pos, field_type_code = fields_sublist[j:j + 3]
                    af_list.append(field_type_code)

                af_array = bytearray(util.make_array_header(len(af_list), util.BYTE_CODE))
                for af in af_list:
                    af_array.append(int(af))
                this_class_lit.extend(af_array)

                # methods array
                methods_arr_ptr = len_before + len(this_class_lit)
                method_list = []

                for method_name in class_parts[methods_index + 1:]:
                    method_list.append(int(function_pointers[method_name][1:]))

                method_array = bytearray(util.make_array_header(len(method_list), util.FUNCTION_CODE))
                for method in method_list:
                    method_array.extend(util.int_to_bytes(method))
                this_class_lit.extend(method_array)

                out_parts = ["class", class_name,
                             "name", f"${class_name_ptr}",
                             "addr", class_ptr,
                             "mro", f"${mro_arr_ptr}",
                             "aligned_fields", f"${af_arr_ptr}",
                             "methods", f"${methods_arr_ptr}"]
                cur_out.append(" ".join(out_parts))
                class_literals.append((classes_before + len(this_class_lit), this_class_lit))
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
                    if inst == "entry":
                        cur_out = entry_out
                        cur_out.append(orig_line)
                    elif inst == "call_fn":
                        fn_name = instructions[1]
                        fn_ptr = function_pointers[fn_name]

                        self.write_format(cur_out, "call", fn_ptr)
                    elif inst == "invoke_fn":
                        fn_name = instructions[1]
                        fn_ptr = native_pointers[fn_name]

                        self.write_format(cur_out, "invoke", fn_ptr)
                    elif inst == "fn":
                        cur_out = body_out
                        if "abstract" in instructions[2:]:
                            if i < length - 2 and len(lines[i + 1].strip()) == 0:
                                i += 1
                        else:
                            cur_out.append(orig_line)
                    elif inst in tpe.PSEUDO_INSTRUCTIONS:
                        self.compile_pseudo_inst(instructions, cur_out, lf)
                    else:
                        cur_out.append(orig_line)
                else:
                    cur_out.append(orig_line)

            i += 1

        class_lit_out = ["class_literals"]
        for end_pos, body in class_literals:
            class_lit_out.append(" ".join([str(b) for b in list(body)]))
        class_lit_out.append("end_class_literals\n")
        # print(class_lit_out)

        return header_out + class_lit_out + class_header_out + body_out + entry_out

    def compile_pseudo_inst(self, inst_line, output: list, lf):
        inst = inst_line[0]
        tup = tpe.PSEUDO_INSTRUCTIONS[inst]
        num_inst = tpe.inst_to_num(inst_line, tup, lf)
        if inst == "load_lit":
            lit_start = self.stack_size + self.global_length
            self.write_format(output, "load", inst_line[1], "$" + str(num_inst[2] + lit_start))
        elif inst == "loadc_lit":
            lit_start = self.stack_size + self.global_length
            self.write_format(output, "loadc", inst_line[1], "$" + str(num_inst[2] + lit_start))
        elif inst == "loadb_lit":
            lit_start = self.stack_size + self.global_length
            self.write_format(output, "loadb", inst_line[1], "$" + str(num_inst[2] + lit_start))
        elif inst == "lit_abs":
            lit_start = self.stack_size + self.global_length
            self.write_format(output, "aload", inst_line[1], "$" + str(num_inst[2] + lit_start))

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
