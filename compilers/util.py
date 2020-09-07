import sys


VM_BITS = 64
INT_LEN = 8
FLOAT_LEN = 8
CHAR_LEN = 1
PTR_LEN = INT_LEN


def replace_extension(file_name: str, ext: str) -> str:
    ind = file_name.rfind(".")
    return file_name[:ind + 1] + ext


def int_to_bytes(i: int) -> bytes:
    return i.to_bytes(INT_LEN, sys.byteorder, signed=True)


def bytes_to_int(b: bytes) -> int:
    return int.from_bytes(b, sys.byteorder, signed=True)


def empty_bytes(length: int) -> bytes:
    return bytes([0 for _ in range(length)])
