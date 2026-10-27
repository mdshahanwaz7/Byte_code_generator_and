# @'
"""
Bytecode opcode definitions for the MiniByte virtual machine.
"""

from enum import Enum, auto


class OpCode(Enum):
    PUSH_CONST = auto()
    POP = auto()
    DUP = auto()

    LOAD_VAR = auto()
    STORE_VAR = auto()

    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    NEG = auto()

    EQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LTE = auto()
    GTE = auto()

    AND = auto()
    OR = auto()
    NOT = auto()

    JUMP = auto()
    JUMP_IF_FALSE = auto()

    CALL = auto()
    RETURN = auto()

    PRINT = auto()

    HALT = auto()


class Instruction:
    __slots__ = ("opcode", "arg")

    def __init__(self, opcode, arg=None):
        self.opcode = opcode
        self.arg = arg

    def __repr__(self):
        if self.arg is not None:
            return self.opcode.name + "(" + repr(self.arg) + ")"
        return self.opcode.name

    def __eq__(self, other):
        if not isinstance(other, Instruction):
            return NotImplemented
        return self.opcode == other.opcode and self.arg == other.arg
# '@ | Set-Content -Path src\compiler\opcodes.py -Encoding UTF8