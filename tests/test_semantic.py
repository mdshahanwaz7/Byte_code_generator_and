"""
Basic tests for the MiniByte semantic analyzer.

Run with:
    python tests/test_semantic.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.semantic.semantic_analyzer import SemanticAnalyzer, SemanticError


def analyze(source):
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    SemanticAnalyzer().analyze(program)


def test_valid_program_passes():
    source = """
    let x = 5;
    let y = x + 2;
    if (y > 0) {
        let z = y * 2;
    }
    """
    analyze(source)


def test_undefined_variable_raises():
    try:
        analyze("let x = y + 1;")
        assert False, "expected SemanticError"
    except SemanticError as e:
        assert "y" in str(e)


def test_assignment_to_undefined_variable_raises():
    try:
        analyze("x = 5;")
        assert False, "expected SemanticError"
    except SemanticError as e:
        assert "x" in str(e)


def test_block_scope_does_not_leak():
    source = """
    if (true) {
        let x = 5;
    }
    let y = x;
    """
    try:
        analyze(source)
        assert False, "expected SemanticError"
    except SemanticError as e:
        assert "x" in str(e)


def test_variable_visible_in_nested_block():
    source = """
    let x = 5;
    if (true) {
        let y = x + 1;
    }
    """
    analyze(source)


def test_function_params_scoped_to_body():
    source = """
    func add(a, b) {
        return a + b;
    }
    let result = add(1, 2);
    """
    analyze(source)


def test_function_param_not_visible_outside():
    source = """
    func add(a, b) {
        return a + b;
    }
    let x = a;
    """
    try:
        analyze(source)
        assert False, "expected SemanticError"
    except SemanticError as e:
        assert "a" in str(e)


def test_undefined_function_call_raises():
    try:
        analyze("let x = doStuff(1, 2);")
        assert False, "expected SemanticError"
    except SemanticError as e:
        assert "doStuff" in str(e)


def test_function_arity_mismatch_raises():
    source = """
    func add(a, b) {
        return a + b;
    }
    let x = add(1);
    """
    try:
        analyze(source)
        assert False, "expected SemanticError"
    except SemanticError as e:
        assert "add" in str(e)


def test_return_outside_function_raises():
    try:
        analyze("return 5;")
        assert False, "expected SemanticError"
    except SemanticError as e:
        assert "return" in str(e)


def test_duplicate_function_definition_raises():
    source = """
    func add(a, b) { return a + b; }
    func add(x, y) { return x - y; }
    """
    try:
        analyze(source)
        assert False, "expected SemanticError"
    except SemanticError as e:
        assert "add" in str(e)


def test_forward_reference_function_call():
    source = """
    func first() {
        return second();
    }
    func second() {
        return 1;
    }
    let x = first();
    """
    analyze(source)


def test_while_loop_scope():
    source = """
    let i = 0;
    while (i < 10) {
        let doubled = i * 2;
        i = i + 1;
    }
    let y = doubled;
    """
    try:
        analyze(source)
        assert False, "expected SemanticError"
    except SemanticError as e:
        assert "doubled" in str(e)


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print("PASS: " + t.__name__)
    print(str(passed) + "/" + str(len(tests)) + " tests passed.")
