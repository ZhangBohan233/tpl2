import sys
import struct


BYTECODE_VERSION = 1

VM_BITS = 32
STACK_SIZE = 2048
INT_PTR_LEN = VM_BITS // 8
FLOAT_LEN = VM_BITS // 8
CHAR_LEN = 2

ZERO_POS = 0
ONE_POS = INT_PTR_LEN
NEG_ONE_POS = INT_PTR_LEN + INT_PTR_LEN

INT_CODE = 1
FLOAT_CODE = 2
CHAR_CODE = 3
BYTE_CODE = 4
OBJECT_CODE = 5
ARRAY_CODE = 6
FUNCTION_CODE = 7
NATIVE_FUNCTION_CODE = 8
CLASS_CODE = 9

STRING_HEADER_LEN = INT_PTR_LEN * 3  # length of string header, should be 'class', 'gcCount', 'chars'
ARRAY_HEADER_LEN = INT_PTR_LEN * 2
FUNC_STACK_HEADER_LEN = INT_PTR_LEN

CHARS_POS_IN_STR = 0  # position of 'chars' in class String

float_pack = "d" if FLOAT_LEN == 8 else "f"


class NaiveDict:
    def __init__(self, checker=None):
        self.keys = []
        self.values = []
        self.checker = checker

    def check(self, v1, v2):
        if self.checker is None:
            return v1 == v2
        else:
            return self.checker(v1, v2)

    def get_entry_by(self, some_key, checker) -> tuple:
        for i in range(len(self)):
            if checker(self.keys[i], some_key):
                return self.keys[i], self.values[i]
        return None

    def get_only(self) -> tuple:
        if len(self) != 1:
            raise IndexError("NaiveDict has not only 1 pairs.")
        return self.keys[0], self.values[0]

    def copy(self):
        cpy = NaiveDict(self.checker)
        cpy.keys.extend(self.keys)
        cpy.values.extend(self.values)
        return cpy

    def __len__(self):
        return len(self.keys)

    def __contains__(self, item):
        try:
            _ = self[item]
            return True
        except IndexError:
            return False

    def __getitem__(self, item):
        for i in range(len(self)):
            if self.check(self.keys[i], item):
                return self.values[i]
        raise IndexError(f"Key '{item}' is not in this NaiveDict.")

    def __setitem__(self, key, value):
        for i in range(len(self)):
            if self.check(self.keys[i], key):
                self.values[i] = value
                return
        self.keys.append(key)
        self.values.append(value)

    def __str__(self):
        kv = []
        for i in range(len(self)):
            kv.append(f"{self.keys[i]}: {self.values[i]}")
        return "NaiveDict{" + ", ".join(kv) + "}"


def set_chars_pos_in_str(pos: int):
    global CHARS_POS_IN_STR
    CHARS_POS_IN_STR = pos


def replace_extension(file_name: str, ext: str) -> str:
    ind = file_name.rfind(".")
    return file_name[:ind + 1] + ext


def u_short_to_bytes(i: int) -> bytes:
    return i.to_bytes(2, sys.byteorder, signed=False)


def int_to_bytes(i: int) -> bytes:
    return i.to_bytes(INT_PTR_LEN, sys.byteorder, signed=True)


def bytes_to_int(b: bytes) -> int:
    return int.from_bytes(b, sys.byteorder, signed=True)


def char_to_bytes(c: str) -> bytes:
    return ord(c).to_bytes(CHAR_LEN, sys.byteorder, signed=False)


def bytes_to_char(b: bytes) -> str:
    return chr(int.from_bytes(b, sys.byteorder, signed=True))


def float_to_bytes(f: float) -> bytes:
    return bytes(struct.pack(float_pack, f))


def bytes_to_float(b: bytes) -> float:
    return struct.unpack(float_pack, b)[0]


def string_to_chars_bytes(s: str) -> bytes:
    res = bytearray(make_array_header(len(s), CHAR_CODE))
    for c in s:
        res.extend(char_to_bytes(c))
    return res


def make_array_header(length, type_code) -> bytes:
    return int_to_bytes(length) + int_to_bytes(type_code)


def make_string_header(str_class_addr: bytes, str_addr: int) -> bytes:
    return str_class_addr + \
           empty_bytes(CHARS_POS_IN_STR - INT_PTR_LEN) + \
           int_to_bytes(str_addr + CHARS_POS_IN_STR + INT_PTR_LEN)  # since in literal, 'chars' array is next to its ptr


def empty_bytes(length: int) -> bytes:
    return bytes([0 for _ in range(length)])


def merge_bytes_to_int(lst: list) -> list:
    assert len(lst) % INT_PTR_LEN == 0
    res = []
    for i in range(0, len(lst), INT_PTR_LEN):
        bs = bytearray()
        for j in range(INT_PTR_LEN):
            bs.append(lst[i + j])
        res.append(bytes_to_int(bs))
    return res


def initial_literal() -> bytearray:
    return bytearray(int_to_bytes(0) + int_to_bytes(1) + int_to_bytes(-1))


def initial_int_literal_dict() -> dict:
    return {0: 0, 1: INT_PTR_LEN, -1: INT_PTR_LEN + INT_PTR_LEN}


def name_with_path(name: str, file: str, clazz):
    if clazz is None:
        return file + "$" + name
    else:
        return class_name_with_path(clazz.name, file) + "." + name


def class_name_with_path(class_name: str, file: str):
    return file + "$" + class_name


def template_full_name(template_name, defined_place: str):
    return defined_place + "." + template_name


def print_warning(msg: str, lfp=""):
    print(f"Warning: {msg} {lfp}", file=sys.stderr)
