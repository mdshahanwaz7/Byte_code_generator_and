"""
Basic tests for the MiniByte parser.

Run with:
    python tests/test_parser.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.lexer.lexer import Lexer
from src.parser.parser import Parser, ParserError
from src.parser.ast_nodes import (
    Program, LetStatement, ExpressionStatement, BlockStatement,
    IfStatement, WhileStatement, FunctionDef, ReturnStatement,
    Identifier, IntLiteral, FloatLiteral, StringLiteral, BoolLiteral,
    UnaryExpr, BinaryExpr, AssignExpr, CallExpr,
)


def parse(source: str) -> Program:
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


def test_let_statement():
    program = parse("let x = 5;")
    assert program == Program([LetStatement("x", IntLiteral(5))])


def test_arithmetic_precedence():
    # 2 + 3 * 4 should parse as 2 + (3 * 4)
    program = parse("let x = 2 + 3 * 4;")
    expected = LetStatement(
        "x",
        BinaryExpr(IntLiteral(2), "+", BinaryExpr(IntLiteral(3), "*", IntLiteral(4))),
    )
    assert program.statements[0] == expected


def test_parentheses_override_precedence():
    # (2 + 3) * 4
    program = parse("let x = (2 + 3) * 4;")
    expected = LetStatement(
        "x",
        BinaryExpr(BinaryExpr(IntLiteral(2), "+", IntLiteral(3)), "*", IntLiteral(4)),
    )
    assert program.statements[0] == expected


def test_comparison_and_logic():
    program = parse("let x = a < 5 && b > 2;")
    expected = LetStatement(
        "x",
        BinaryExpr(
            BinaryExpr(Identifier("a"), "<", IntLiteral(5)),
            "&&",
            BinaryExpr(Identifier("b"), ">", IntLiteral(2)),
        ),
    )
    assert program.statements[0] == expected


def test_unary_expressions():
    program = parse("let x = -5; let y = !true;")
    assert program.statements[0] == LetStatement("x", UnaryExpr("-", IntLiteral(5)))
    assert program.statements[1] == LetStatement("y", UnaryExpr("!", BoolLiteral(True)))


def test_assignment_expression():
    program = parse("x = 10;")
    assert program.statements[0] == ExpressionStatement(AssignExpr("x", IntLiteral(10)))


def test_if_else_statement():
    source = """
    if (x > 0) {
        return 1;
    } else {
        return 0;
    }
    """
    program = parse(source)
    expected = IfStatement(
        BinaryExpr(Identifier("x"), ">", IntLiteral(0)),
        BlockStatement([ReturnStatement(IntLiteral(1))]),
        BlockStatement([ReturnStatement(IntLiteral(0))]),
    )
    assert program.statements[0] == expected


def test_while_statement():
    source = """
    while (i < 10) {
        i = i + 1;
    }
    """
    program = parse(source)
    expected = WhileStatement(
        BinaryExpr(Identifier("i"), "<", IntLiteral(10)),
        BlockStatement([ExpressionStatement(AssignExpr("i", BinaryExpr(Identifier("i"), "+", IntLiteral(1))))]),
    )
    assert program.statements[0] == expected


def test_function_definition_and_call():
    source = """
    func add(a, b) {
        return a + b;
    }
    let result = add(2, 3);
    """
    program = parse(source)
    func_def = FunctionDef(
        "add", ["a", "b"],
        BlockStatement([ReturnStatement(BinaryExpr(Identifier("a"), "+", Identifier("b")))]),
    )
    call_stmt = LetStatement("result", CallExpr("add", [IntLiteral(2), IntLiteral(3)]))
    assert program.statements[0] == func_def
    assert program.statements[1] == call_stmt


def test_string_and_float_literals():
    program = parse('let s = "hello"; let f = 3.14;')
    assert program.statements[0] == LetStatement("s", StringLiteral("hello"))
    assert program.statements[1] == LetStatement("f", FloatLiteral(3.14))


def test_missing_semicolon_raises():
    try:
        parse("let x = 5")
        assert False, "expected ParserError"
    except ParserError:
        pass


def test_invalid_assignment_target_raises():
    try:
        parse("5 = x;")
        assert False, "expected ParserError"
    except ParserError:
        pass


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"PASS: {t.__name__}")
    print(f"\n{passed}/{len(tests)} tests passed.")