import sys
import struct


VM_BITS = 32
STACK_SIZE = 2048
INT_LEN = VM_BITS // 8
FLOAT_LEN = VM_BITS // 8
CHAR_LEN = 2
PTR_LEN = INT_LEN

ZERO_POS = 0
ONE_POS = INT_LEN
NEG_ONE_POS = INT_LEN + INT_LEN

STRING_HEADER_LEN = PTR_LEN * 2

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


def replace_extension(file_name: str, ext: str) -> str:
    ind = file_name.rfind(".")
    return file_name[:ind + 1] + ext


def int_to_bytes(i: int) -> bytes:
    return i.to_bytes(INT_LEN, sys.byteorder, signed=True)


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


def string_to_bytes(s: str) -> bytes:
    res = bytearray(int_to_bytes(len(s)))
    for c in s:
        res.extend(char_to_bytes(c))
    return res


def empty_bytes(length: int) -> bytes:
    return bytes([0 for _ in range(length)])


def initial_literal() -> bytearray:
    return bytearray(int_to_bytes(0) + int_to_bytes(1) + int_to_bytes(-1))


def initial_int_literal_dict() -> dict:
    return {0: 0, 1: INT_LEN, -1: INT_LEN + INT_LEN}


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
