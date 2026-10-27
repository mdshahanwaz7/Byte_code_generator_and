
"""
Binary bytecode format for MiniByte (.mbc files).

Converts the compiler's instruction list into real bytes, and back.

File layout (all multi-byte numbers are big-endian):

    Header      4 bytes   magic "MBYT"
                1 byte    format version (currently 1)
    Constants   2 bytes   count, then each constant as:
                            tag 1 = int    -> 8 bytes (signed 64-bit)
                            tag 2 = float  -> 8 bytes (IEEE 754 double)
                            tag 3 = string -> 2-byte length + UTF-8 bytes
                            tag 4 = bool   -> 1 byte (0 or 1)
    Names       2 bytes   count, then each name as 2-byte length + UTF-8 bytes
                          (variable names and function names share this table)
    Functions   2 bytes   count, then each as:
                            2 bytes name index, 4 bytes start address, 1 byte arity
    Code        4 bytes   instruction count, then that many 4-byte instructions

Every instruction is exactly 4 bytes: 1 opcode byte + a 3-byte operand.
This fixed width means instruction N starts at byte N * 4 of the code
section, and jump targets are simply instruction numbers.

    opcode   operand (3 bytes)
    -------  --------------------------------------------------------
    PUSH_CONST       index into the constants table
    LOAD_VAR/STORE_VAR   index into the names table
    JUMP/JUMP_IF_FALSE   target instruction number
    CALL             name index (upper 2 bytes) + argument count (last byte)
    PRINT            argument count
    everything else  0
"""

import struct

from src.compiler.opcodes import OpCode, Instruction


MAGIC = b"MBYT"
VERSION = 1


class BytecodeError(Exception):
    """Raised for invalid programs when encoding, or corrupt files when decoding."""


# Explicit, stable byte values. These are part of the file format, so they
# must never depend on the order of the OpCode enum.
_OPCODE_TO_BYTE = {
    OpCode.PUSH_CONST: 0x01,
    OpCode.POP: 0x02,
    OpCode.DUP: 0x03,
    OpCode.LOAD_VAR: 0x10,
    OpCode.STORE_VAR: 0x11,
    OpCode.ADD: 0x20,
    OpCode.SUB: 0x21,
    OpCode.MUL: 0x22,
    OpCode.DIV: 0x23,
    OpCode.MOD: 0x24,
    OpCode.NEG: 0x25,
    OpCode.EQ: 0x30,
    OpCode.NEQ: 0x31,
    OpCode.LT: 0x32,
    OpCode.GT: 0x33,
    OpCode.LTE: 0x34,
    OpCode.GTE: 0x35,
    OpCode.AND: 0x40,
    OpCode.OR: 0x41,
    OpCode.NOT: 0x42,
    OpCode.JUMP: 0x50,
    OpCode.JUMP_IF_FALSE: 0x51,
    OpCode.CALL: 0x60,
    OpCode.RETURN: 0x61,
    OpCode.PRINT: 0x70,
    OpCode.HALT: 0xFF,
}
_BYTE_TO_OPCODE = {byte: op for op, byte in _OPCODE_TO_BYTE.items()}

_CONST_OPS = {OpCode.PUSH_CONST}
_NAME_OPS = {OpCode.LOAD_VAR, OpCode.STORE_VAR}
_JUMP_OPS = {OpCode.JUMP, OpCode.JUMP_IF_FALSE}
_COUNT_OPS = {OpCode.PRINT}

_TAG_INT = 1
_TAG_FLOAT = 2
_TAG_STRING = 3
_TAG_BOOL = 4

_MAX_OPERAND = 0xFFFFFF
_MAX_TABLE_SIZE = 0xFFFF


# ---------------------------------------------------------------- encoding

def encode(instructions, functions) -> bytes:
    """Convert (instructions, functions) from the compiler into .mbc bytes."""
    constants = []
    constant_ids = {}
    names = []
    name_ids = {}

    def constant_id(value):
        # Keyed by type too, so True, 1 and 1.0 stay three separate constants.
        key = (type(value), value)
        if key not in constant_ids:
            constant_ids[key] = len(constants)
            constants.append(value)
        return constant_ids[key]

    def name_id(name):
        if name not in name_ids:
            name_ids[name] = len(names)
            names.append(name)
        return name_ids[name]

    total = len(instructions)
    code = bytearray()

    for pos, instr in enumerate(instructions):
        op = instr.opcode
        if op not in _OPCODE_TO_BYTE:
            raise BytecodeError(f"instruction {pos}: opcode {op} has no byte value")

        if op in _CONST_OPS:
            operand = constant_id(instr.arg)
        elif op in _NAME_OPS:
            operand = name_id(instr.arg)
        elif op in _JUMP_OPS:
            target = instr.arg
            if isinstance(target, bool) or not isinstance(target, int) or not 0 <= target < total:
                raise BytecodeError(f"instruction {pos}: invalid jump target {target!r}")
            operand = target
        elif op == OpCode.CALL:
            name, arg_count = instr.arg
            if not 0 <= arg_count <= 0xFF:
                raise BytecodeError(f"instruction {pos}: too many arguments ({arg_count})")
            index = name_id(name)
            if index > _MAX_TABLE_SIZE:
                raise BytecodeError("program uses too many distinct names")
            operand = (index << 8) | arg_count
        elif op in _COUNT_OPS:
            operand = instr.arg
        else:
            if instr.arg is not None:
                raise BytecodeError(f"instruction {pos}: {op.name} takes no operand")
            operand = 0

        if not 0 <= operand <= _MAX_OPERAND:
            raise BytecodeError(f"instruction {pos}: operand {operand} does not fit in 3 bytes")
        code += bytes([_OPCODE_TO_BYTE[op]]) + operand.to_bytes(3, "big")

    function_entries = []
    for fname, (address, arity) in functions.items():
        if not 0 <= address < total:
            raise BytecodeError(f"function '{fname}': start address {address} is out of range")
        if not 0 <= arity <= 0xFF:
            raise BytecodeError(f"function '{fname}': too many parameters ({arity})")
        function_entries.append((name_id(fname), address, arity))

    if len(constants) > _MAX_TABLE_SIZE:
        raise BytecodeError("program has too many constants")
    if len(names) > _MAX_TABLE_SIZE:
        raise BytecodeError("program uses too many distinct names")

    out = bytearray()
    out += MAGIC
    out += bytes([VERSION])

    out += struct.pack(">H", len(constants))
    for value in constants:
        out += _encode_constant(value)

    out += struct.pack(">H", len(names))
    for name in names:
        out += _encode_string(name)

    out += struct.pack(">H", len(function_entries))
    for index, address, arity in function_entries:
        out += struct.pack(">HIB", index, address, arity)

    out += struct.pack(">I", total)
    out += code
    return bytes(out)


def _encode_string(text: str) -> bytes:
    data = text.encode("utf-8")
    if len(data) > 0xFFFF:
        raise BytecodeError("string or name longer than 65535 bytes")
    return struct.pack(">H", len(data)) + data


def _encode_constant(value) -> bytes:
    if isinstance(value, bool):  # must be checked before int: bool is an int subclass
        return bytes([_TAG_BOOL, 1 if value else 0])
    if isinstance(value, int):
        if not -(2 ** 63) <= value < 2 ** 63:
            raise BytecodeError(f"integer constant {value} does not fit in 64 bits")
        return bytes([_TAG_INT]) + struct.pack(">q", value)
    if isinstance(value, float):
        return bytes([_TAG_FLOAT]) + struct.pack(">d", value)
    if isinstance(value, str):
        return bytes([_TAG_STRING]) + _encode_string(value)
    raise BytecodeError(f"unsupported constant type {type(value).__name__}")


# ---------------------------------------------------------------- decoding

class _Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def read(self, count: int) -> bytes:
        end = self.pos + count
        if end > len(self.data):
            raise BytecodeError("unexpected end of file (bytecode is truncated)")
        chunk = self.data[self.pos:end]
        self.pos = end
        return chunk

    def unpack(self, fmt: str):
        return struct.unpack(fmt, self.read(struct.calcsize(fmt)))


def decode(data: bytes):
    """Convert .mbc bytes back into (instructions, functions) for the VM."""
    reader = _Reader(bytes(data))

    if reader.read(4) != MAGIC:
        raise BytecodeError("not a MiniByte bytecode file (bad magic number)")
    (version,) = reader.unpack(">B")
    if version != VERSION:
        raise BytecodeError(f"unsupported bytecode version {version} (expected {VERSION})")

    (constant_count,) = reader.unpack(">H")
    constants = [_read_constant(reader) for _ in range(constant_count)]

    (name_count,) = reader.unpack(">H")
    names = [_read_string(reader) for _ in range(name_count)]

    (function_count,) = reader.unpack(">H")
    raw_functions = [reader.unpack(">HIB") for _ in range(function_count)]

    (total,) = reader.unpack(">I")
    code = reader.read(total * 4)
    if reader.pos != len(reader.data):
        raise BytecodeError("unexpected extra bytes after the code section")

    def lookup(table, index, what, where):
        if index >= len(table):
            raise BytecodeError(f"{where}: {what} index {index} is out of range")
        return table[index]

    instructions = []
    for pos in range(total):
        word = code[pos * 4:pos * 4 + 4]
        op = _BYTE_TO_OPCODE.get(word[0])
        if op is None:
            raise BytecodeError(f"instruction {pos}: unknown opcode byte 0x{word[0]:02X}")
        operand = int.from_bytes(word[1:], "big")

        if op in _CONST_OPS:
            arg = lookup(constants, operand, "constant", f"instruction {pos}")
        elif op in _NAME_OPS:
            arg = lookup(names, operand, "name", f"instruction {pos}")
        elif op in _JUMP_OPS:
            if operand >= total:
                raise BytecodeError(f"instruction {pos}: jump target {operand} is out of range")
            arg = operand
        elif op == OpCode.CALL:
            arg = (lookup(names, operand >> 8, "name", f"instruction {pos}"), operand & 0xFF)
        elif op in _COUNT_OPS:
            arg = operand
        else:
            if operand != 0:
                raise BytecodeError(f"instruction {pos}: {op.name} should have no operand")
            arg = None
        instructions.append(Instruction(op, arg))

    functions = {}
    for name_index, address, arity in raw_functions:
        name = lookup(names, name_index, "name", "function table")
        if address >= total:
            raise BytecodeError(f"function '{name}': start address {address} is out of range")
        functions[name] = (address, arity)

    return instructions, functions


def _read_string(reader: _Reader) -> str:
    (length,) = reader.unpack(">H")
    raw = reader.read(length)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise BytecodeError("string in bytecode is not valid UTF-8")


def _read_constant(reader: _Reader):
    (tag,) = reader.unpack(">B")
    if tag == _TAG_INT:
        return reader.unpack(">q")[0]
    if tag == _TAG_FLOAT:
        return reader.unpack(">d")[0]
    if tag == _TAG_STRING:
        return _read_string(reader)
    if tag == _TAG_BOOL:
        (flag,) = reader.unpack(">B")
        if flag not in (0, 1):
            raise BytecodeError(f"invalid boolean constant byte {flag}")
        return flag == 1
    raise BytecodeError(f"unknown constant tag {tag}")


# ------------------------------------------------------------------ viewing

def hexdump(data: bytes, width: int = 16) -> str:
    """Return a classic hex dump: offset, hex bytes, printable characters."""
    lines = []
    for offset in range(0, len(data), width):
        chunk = data[offset:offset + width]
        hex_part = " ".join(f"{b:02X}" for b in chunk)
        text_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{offset:08X}  {hex_part:<{width * 3 - 1}}  {text_part}")
    return "\n".join(lines)
