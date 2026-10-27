"""
Basic tests for the MiniByte lexer.

Run with:
    python -m pytest tests/test_lexer.py -v
or simply:
    python tests/test_lexer.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.lexer.lexer import Lexer, LexerError
from src.lexer.token_type import TokenType


def token_types(source: str):
    tokens = Lexer(source).tokenize()
    return [t.type for t in tokens]


def test_basic_assignment():
    types = token_types("let x = 5;")
    assert types == [
        TokenType.LET,
        TokenType.IDENTIFIER,
        TokenType.ASSIGN,
        TokenType.INT,
        TokenType.SEMICOLON,
        TokenType.EOF,
    ]


def test_float_literal():
    tokens = Lexer("let pi = 3.14;").tokenize()
    assert tokens[3].type == TokenType.FLOAT
    assert tokens[3].value == 3.14


def test_string_literal():
    tokens = Lexer('let name = "MiniByte";').tokenize()
    assert tokens[3].type == TokenType.STRING
    assert tokens[3].value == "MiniByte"


def test_operators():
    types = token_types("== != <= >= && || ! + - * / %")
    expected = [
        TokenType.EQ, TokenType.NEQ, TokenType.LTE, TokenType.GTE,
        TokenType.AND, TokenType.OR, TokenType.NOT,
        TokenType.PLUS, TokenType.MINUS, TokenType.STAR,
        TokenType.SLASH, TokenType.PERCENT, TokenType.EOF,
    ]
    assert types == expected


def test_keywords():
    types = token_types("if else while func return true false")
    expected = [
        TokenType.IF, TokenType.ELSE, TokenType.WHILE, TokenType.FUNC,
        TokenType.RETURN, TokenType.TRUE, TokenType.FALSE, TokenType.EOF,
    ]
    assert types == expected


def test_comments_are_skipped():
    types = token_types("let x = 1; // this is a comment\nlet y = 2;")
    assert TokenType.IDENTIFIER in types
    assert types.count(TokenType.LET) == 2


def test_function_definition():
    source = """
    func add(a, b) {
        return a + b;
    }
    """
    types = token_types(source)
    expected = [
        TokenType.FUNC, TokenType.IDENTIFIER, TokenType.LPAREN,
        TokenType.IDENTIFIER, TokenType.COMMA, TokenType.IDENTIFIER,
        TokenType.RPAREN, TokenType.LBRACE,
        TokenType.RETURN, TokenType.IDENTIFIER, TokenType.PLUS,
        TokenType.IDENTIFIER, TokenType.SEMICOLON,
        TokenType.RBRACE, TokenType.EOF,
    ]
    assert types == expected


def test_unterminated_string_raises():
    try:
        Lexer('let x = "oops;').tokenize()
        assert False, "expected LexerError"
    except LexerError:
        pass


def test_unexpected_character_raises():
    try:
        Lexer("let x = 5 @ 3;").tokenize()
        assert False, "expected LexerError"
    except LexerError:
        pass


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"PASS: {t.__name__}")
    print(f"\n{passed}/{len(tests)} tests passed.")