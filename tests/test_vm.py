import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.semantic.semantic_analyzer import SemanticAnalyzer
from src.compiler.compiler import Compiler
from src.vm.vm import VM, VMError


def run_program(source):
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    SemanticAnalyzer().analyze(program)
    instructions, functions = Compiler().compile(program)
    vm = VM(instructions, functions)
    vm.run()
    return vm


def test_arithmetic_with_precedence():
    vm = run_program("let x = 2 + 3 * 4;")
    assert vm.global_vars["x"] == 14


def test_parentheses_override_precedence():
    vm = run_program("let x = (2 + 3) * 4;")
    assert vm.global_vars["x"] == 20


def test_division_and_modulo():
    vm = run_program("let a = 7 / 2; let b = 7 % 2;")
    assert vm.global_vars["a"] == 3.5
    assert vm.global_vars["b"] == 1


def test_division_by_zero_raises():
    try:
        run_program("let x = 1 / 0;")
        assert False, "expected VMError"
    except VMError as e:
        assert "zero" in str(e).lower()


def test_string_concatenation():
    vm = run_program('let s = "Mini" + "Byte";')
    assert vm.global_vars["s"] == "MiniByte"


def test_comparison_and_boolean_logic():
    vm = run_program("let a = 5 > 3; let b = 5 > 3 && 2 < 1; let c = 5 > 3 || 2 < 1;")
    assert vm.global_vars["a"] is True
    assert vm.global_vars["b"] is False
    assert vm.global_vars["c"] is True


def test_unary_operators():
    vm = run_program("let a = -5; let b = !true; let c = !false;")
    assert vm.global_vars["a"] == -5
    assert vm.global_vars["b"] is False
    assert vm.global_vars["c"] is True


def test_if_else_branching():
    source = """
    let x = 10;
    let result = 0;
    if (x > 5) {
        result = 1;
    } else {
        result = 2;
    }
    """
    vm = run_program(source)
    assert vm.global_vars["result"] == 1


def test_if_else_false_branch():
    source = """
    let x = 1;
    let result = 0;
    if (x > 5) {
        result = 1;
    } else {
        result = 2;
    }
    """
    vm = run_program(source)
    assert vm.global_vars["result"] == 2


def test_while_loop_sums_to_ten():
    source = """
    let i = 0;
    let total = 0;
    while (i < 5) {
        total = total + i;
        i = i + 1;
    }
    """
    vm = run_program(source)
    assert vm.global_vars["total"] == 10
    assert vm.global_vars["i"] == 5


def test_simple_function_call():
    source = """
    func add(a, b) {
        return a + b;
    }
    let result = add(3, 4);
    """
    vm = run_program(source)
    assert vm.global_vars["result"] == 7


def test_recursive_function_factorial():
    source = """
    func factorial(n) {
        if (n <= 1) {
            return 1;
        } else {
            return n * factorial(n - 1);
        }
    }
    let result = factorial(5);
    """
    vm = run_program(source)
    assert vm.global_vars["result"] == 120


def test_recursive_function_fibonacci():
    source = """
    func fib(n) {
        if (n < 2) {
            return n;
        } else {
            return fib(n - 1) + fib(n - 2);
        }
    }
    let result = fib(10);
    """
    vm = run_program(source)
    assert vm.global_vars["result"] == 55


def test_function_params_do_not_leak_to_global():
    source = """
    func square(n) {
        return n * n;
    }
    let result = square(6);
    """
    vm = run_program(source)
    assert vm.global_vars["result"] == 36
    assert "n" not in vm.global_vars


def test_undefined_variable_at_runtime_raises():
    tokens = Lexer("x;").tokenize()
    from src.parser.ast_nodes import Program, ExpressionStatement, Identifier
    program = Program([ExpressionStatement(Identifier("x"))])
    instructions, functions = Compiler().compile(program)
    vm = VM(instructions, functions)
    try:
        vm.run()
        assert False, "expected VMError"
    except VMError as e:
        assert "x" in str(e)


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print("PASS: " + t.__name__)
    print(str(passed) + "/" + str(len(tests)) + " tests passed.")
