import sys
import struct


VM_BITS = 64
STACK_SIZE = 1024
INT_LEN = 8
FLOAT_LEN = 8
CHAR_LEN = 2
PTR_LEN = INT_LEN

FALSE_POS = 0
TRUE_POS = INT_LEN

float_pack = "d" if FLOAT_LEN == 8 else "f"


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


def empty_bytes(length: int) -> bytes:
    return bytes([0 for _ in range(length)])


def initial_literal() -> bytearray:
    return bytearray(int_to_bytes(0) + int_to_bytes(1))  # false and true, related to FALSE_POS and TRUE_POS


def initial_int_literal_dict() -> dict:
    return {0: 0, 1: INT_LEN}


def name_with_path(name: str, file: str):
    return file + "$" + name
