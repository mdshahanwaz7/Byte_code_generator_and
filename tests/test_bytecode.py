# @'
"""
Tests for MiniByte's binary bytecode format (.mbc).

Run with:
    python tests/test_bytecode.py
"""

import sys
import os
import io
import contextlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.semantic.semantic_analyzer import SemanticAnalyzer
from src.compiler.compiler import Compiler
from src.compiler.opcodes import OpCode, Instruction
from src.compiler.bytecode import encode, decode, hexdump, BytecodeError, MAGIC
from src.vm.vm import VM


def compile_source(source):
    program = Parser(Lexer(source).tokenize()).parse()
    SemanticAnalyzer().analyze(program)
    return Compiler().compile(program)


def run(instructions, functions):
    """Run a program; return (global variables, printed text)."""
    vm = VM(instructions, functions)
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        vm.run()
    return vm.global_vars, buffer.getvalue()


def expect_error(data):
    try:
        decode(data)
    except BytecodeError:
        return
    assert False, "expected BytecodeError"


FACTORIAL = """
func factorial(n) {
    if (n <= 1) { return 1; }
    return n * factorial(n - 1);
}
let result = factorial(6);
let i = 0;
while (i < 3) {
    print("i =", i);
    i = i + 1;
}
"""


def test_header_has_magic_and_version():
    instructions, functions = compile_source("let x = 5;")
    data = encode(instructions, functions)
    assert data[:4] == MAGIC == b"MBYT"
    assert data[4] == 1


def test_exact_size_of_small_program():
    # header 5 + constants (2 + 9) + names (2 + 3) + functions 2 + code (4 + 3*4)
    instructions, functions = compile_source("let x = 5;")
    assert len(encode(instructions, functions)) == 39


def test_every_instruction_is_four_bytes():
    instructions, functions = compile_source(FACTORIAL)
    data = encode(instructions, functions)
    code_size = 4 * len(instructions)
    assert data[-code_size:][0] in (0x50, 0x01)  # starts with a real opcode word
    # the 4 bytes before the code section hold the instruction count
    count = int.from_bytes(data[-code_size - 4:-code_size], "big")
    assert count == len(instructions)


def test_roundtrip_simple_program():
    instructions, functions = compile_source("let x = 5; let y = x * 2 + 1;")
    decoded, decoded_functions = decode(encode(instructions, functions))
    assert decoded == instructions
    assert decoded_functions == functions


def test_roundtrip_preserves_function_table():
    instructions, functions = compile_source(FACTORIAL)
    decoded, decoded_functions = decode(encode(instructions, functions))
    assert decoded == instructions
    assert decoded_functions == functions
    assert "factorial" in decoded_functions


def test_all_value_types_roundtrip():
    source = 'let a = 42; let b = 3.14; let c = "h\u00e9llo w\u00f6rld"; let d = true; let e = false;'
    instructions, functions = compile_source(source)
    decoded, _ = decode(encode(instructions, functions))
    constants = [i.arg for i in decoded if i.opcode == OpCode.PUSH_CONST]
    assert constants == [42, 3.14, "h\u00e9llo w\u00f6rld", True, False]
    assert [type(c) for c in constants] == [int, float, str, bool, bool]


def test_constants_are_deduplicated():
    instructions, functions = compile_source("let a = 5; let b = 5; let c = 5;")
    data = encode(instructions, functions)
    constant_count = int.from_bytes(data[5:7], "big")
    assert constant_count == 1


def test_true_and_one_are_not_merged():
    instructions, functions = compile_source("let a = true; let b = 1;")
    data = encode(instructions, functions)
    constant_count = int.from_bytes(data[5:7], "big")
    assert constant_count == 2
    decoded, _ = decode(data)
    values = [i.arg for i in decoded if i.opcode == OpCode.PUSH_CONST]
    assert values[0] is True and values[1] == 1 and values[1] is not True


def test_program_behaves_identically_after_roundtrip():
    instructions, functions = compile_source(FACTORIAL)
    direct = run(instructions, functions)
    decoded, decoded_functions = decode(encode(instructions, functions))
    from_bytes = run(decoded, decoded_functions)
    assert direct == from_bytes
    assert from_bytes[0]["result"] == 720
    assert from_bytes[1] == "i = 0\ni = 1\ni = 2\n"


def test_comparison_operators_survive_the_pipeline():
    # If this fails, the lexer fix for ==, !=, <=, >= has not been applied.
    source = "let a = 1 <= 2; let b = 2 >= 3; let c = 2 == 2; let d = 2 != 2;"
    instructions, functions = compile_source(source)
    ops = [i.opcode for i in instructions]
    assert OpCode.LTE in ops and OpCode.GTE in ops and OpCode.EQ in ops and OpCode.NEQ in ops
    decoded, decoded_functions = decode(encode(instructions, functions))
    variables, _ = run(decoded, decoded_functions)
    assert variables == {"a": True, "b": False, "c": True, "d": False}


def test_bad_magic_is_rejected():
    instructions, functions = compile_source("let x = 5;")
    data = bytearray(encode(instructions, functions))
    data[0] = ord("X")
    expect_error(bytes(data))


def test_unsupported_version_is_rejected():
    instructions, functions = compile_source("let x = 5;")
    data = bytearray(encode(instructions, functions))
    data[4] = 99
    expect_error(bytes(data))


def test_every_truncation_is_rejected():
    instructions, functions = compile_source(FACTORIAL)
    data = encode(instructions, functions)
    for length in range(len(data)):
        expect_error(data[:length])


def test_trailing_bytes_are_rejected():
    instructions, functions = compile_source("let x = 5;")
    expect_error(encode(instructions, functions) + b"\x00")


def test_unknown_opcode_is_rejected():
    instructions, functions = compile_source("let x = 5;")
    data = bytearray(encode(instructions, functions))
    data[-12] = 0xEE  # first instruction's opcode byte
    expect_error(bytes(data))


def test_out_of_range_jump_is_rejected_when_decoding():
    data = bytearray(encode([Instruction(OpCode.JUMP, 1), Instruction(OpCode.HALT)], {}))
    data[-5] = 99  # last operand byte of the JUMP instruction
    expect_error(bytes(data))


def test_invalid_jump_is_rejected_when_encoding():
    try:
        encode([Instruction(OpCode.JUMP, 99), Instruction(OpCode.HALT)], {})
        assert False, "expected BytecodeError"
    except BytecodeError:
        pass


def test_oversized_integer_is_rejected_when_encoding():
    try:
        encode([Instruction(OpCode.PUSH_CONST, 2 ** 70), Instruction(OpCode.HALT)], {})
        assert False, "expected BytecodeError"
    except BytecodeError:
        pass


def test_hexdump_format():
    dump = hexdump(b"MBYT\x01")
    assert dump.startswith("00000000  4D 42 59 54 01")
    assert dump.endswith("MBYT.")


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"PASS: {t.__name__}")
    print(f"\n{passed}/{len(tests)} tests passed.")
# '@ | Set-Content -Path tests\test_bytecode.py -Encoding UTF8