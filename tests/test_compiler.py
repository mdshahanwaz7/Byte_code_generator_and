import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.compiler.compiler import Compiler
from src.compiler.opcodes import OpCode, Instruction


def compile_source(source):
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    return Compiler().compile(program)


def op_sequence(instructions):
    return [instr.opcode for instr in instructions]


def test_simple_let():
    instructions, functions = compile_source("let x = 5;")
    assert instructions == [
        Instruction(OpCode.PUSH_CONST, 5),
        Instruction(OpCode.STORE_VAR, "x"),
        Instruction(OpCode.HALT),
    ]
    assert functions == {}


def test_arithmetic_precedence_compiles_correctly():
    instructions, _ = compile_source("let x = 2 + 3 * 4;")
    assert op_sequence(instructions) == [
        OpCode.PUSH_CONST, OpCode.PUSH_CONST, OpCode.PUSH_CONST,
        OpCode.MUL, OpCode.ADD, OpCode.STORE_VAR, OpCode.HALT,
    ]


def test_expression_statement_emits_pop():
    instructions, _ = compile_source("5 + 3;")
    assert op_sequence(instructions) == [
        OpCode.PUSH_CONST, OpCode.PUSH_CONST, OpCode.ADD, OpCode.POP, OpCode.HALT,
    ]


def test_assignment_expression_duplicates_value():
    instructions, _ = compile_source("let x = 1; x = 5;")
    assert op_sequence(instructions) == [
        OpCode.PUSH_CONST, OpCode.STORE_VAR,
        OpCode.PUSH_CONST, OpCode.DUP, OpCode.STORE_VAR, OpCode.POP,
        OpCode.HALT,
    ]


def test_if_without_else():
    source = "if (x > 0) { let y = 1; }"
    instructions, _ = compile_source(source)
    assert op_sequence(instructions) == [
        OpCode.LOAD_VAR, OpCode.PUSH_CONST, OpCode.GT,
        OpCode.JUMP_IF_FALSE,
        OpCode.PUSH_CONST, OpCode.STORE_VAR,
        OpCode.HALT,
    ]
    jump_instr = instructions[3]
    assert jump_instr.arg == 6


def test_if_with_else():
    source = "if (x > 0) { let y = 1; } else { let y = 2; }"
    instructions, _ = compile_source(source)
    assert op_sequence(instructions) == [
        OpCode.LOAD_VAR, OpCode.PUSH_CONST, OpCode.GT,
        OpCode.JUMP_IF_FALSE,
        OpCode.PUSH_CONST, OpCode.STORE_VAR,
        OpCode.JUMP,
        OpCode.PUSH_CONST, OpCode.STORE_VAR,
        OpCode.HALT,
    ]
    else_jump = instructions[3]
    end_jump = instructions[6]
    assert else_jump.arg == 7
    assert end_jump.arg == 9


def test_while_loop_jumps_back():
    source = "while (i < 10) { i = i + 1; }"
    instructions, _ = compile_source(source)
    assert op_sequence(instructions) == [
        OpCode.LOAD_VAR, OpCode.PUSH_CONST, OpCode.LT,
        OpCode.JUMP_IF_FALSE,
        OpCode.LOAD_VAR, OpCode.PUSH_CONST, OpCode.ADD,
        OpCode.DUP, OpCode.STORE_VAR, OpCode.POP,
        OpCode.JUMP,
        OpCode.HALT,
    ]
    jump_back = instructions[10]
    exit_jump = instructions[3]
    assert jump_back.arg == 0
    assert exit_jump.arg == 11


def test_function_compiles_with_entry_in_table():
    source = """
    func add(a, b) {
        return a + b;
    }
    let result = add(2, 3);
    """
    instructions, functions = compile_source(source)
    assert "add" in functions
    start_address, arity = functions["add"]
    assert arity == 2
    assert start_address == 1
    assert instructions[0].opcode == OpCode.JUMP

    func_body = instructions[start_address:start_address + 2]
    assert [i.opcode for i in func_body] == [OpCode.STORE_VAR, OpCode.STORE_VAR]
    assert func_body[0].arg == "b"
    assert func_body[1].arg == "a"


def test_function_call_emits_call_instruction():
    source = """
    func add(a, b) {
        return a + b;
    }
    let result = add(2, 3);
    """
    instructions, _ = compile_source(source)
    call_instrs = [i for i in instructions if i.opcode == OpCode.CALL]
    assert len(call_instrs) == 1
    assert call_instrs[0].arg == ("add", 2)


def test_function_without_explicit_return_gets_implicit_one():
    source = """
    func noop() {
        let x = 1;
    }
    """
    instructions, functions = compile_source(source)
    start, _ = functions["noop"]
    assert instructions[start + 2].opcode == OpCode.PUSH_CONST
    assert instructions[start + 3].opcode == OpCode.RETURN


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print("PASS: " + t.__name__)
    print(str(passed) + "/" + str(len(tests)) + " tests passed.")
