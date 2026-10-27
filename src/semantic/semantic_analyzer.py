# @'
"""
Semantic analyzer for the MiniByte language.
"""

from src.parser.ast_nodes import (
    Program, LetStatement, ExpressionStatement, BlockStatement,
    IfStatement, WhileStatement, FunctionDef, ReturnStatement,
    Identifier, IntLiteral, FloatLiteral, StringLiteral, BoolLiteral,
    UnaryExpr, BinaryExpr, AssignExpr, CallExpr,
)


class SemanticError(Exception):
    pass


BUILTIN_FUNCTIONS = {"print"}


class Scope:
    def __init__(self, parent=None):
        self.vars = set()
        self.parent = parent

    def define(self, name):
        self.vars.add(name)

    def is_defined(self, name):
        if name in self.vars:
            return True
        if self.parent is not None:
            return self.parent.is_defined(name)
        return False


class SemanticAnalyzer:
    def __init__(self):
        self.functions = {}
        self.current_scope = Scope()
        self.function_depth = 0

    def analyze(self, program):
        for stmt in program.statements:
            if isinstance(stmt, FunctionDef):
                if stmt.name in BUILTIN_FUNCTIONS:
                    raise SemanticError("'" + stmt.name + "' is a reserved built-in function and cannot be redefined")
                if stmt.name in self.functions:
                    raise SemanticError("Function '" + stmt.name + "' is already defined")
                self.functions[stmt.name] = len(stmt.params)

        for stmt in program.statements:
            self._visit(stmt)

    def _visit(self, node):
        method_name = "_visit_" + type(node).__name__
        method = getattr(self, method_name, None)
        if method is None:
            raise SemanticError("No semantic visitor for node type " + type(node).__name__)
        return method(node)

    def _visit_LetStatement(self, node):
        self._visit(node.value)
        self.current_scope.define(node.name)

    def _visit_ExpressionStatement(self, node):
        self._visit(node.expression)

    def _visit_BlockStatement(self, node):
        enclosing = self.current_scope
        self.current_scope = Scope(enclosing)
        for stmt in node.statements:
            self._visit(stmt)
        self.current_scope = enclosing

    def _visit_IfStatement(self, node):
        self._visit(node.condition)
        self._visit(node.then_branch)
        if node.else_branch is not None:
            self._visit(node.else_branch)

    def _visit_WhileStatement(self, node):
        self._visit(node.condition)
        self._visit(node.body)

    def _visit_FunctionDef(self, node):
        enclosing = self.current_scope
        self.current_scope = Scope(enclosing)
        for param in node.params:
            self.current_scope.define(param)

        self.function_depth += 1
        for stmt in node.body.statements:
            self._visit(stmt)
        self.function_depth -= 1

        self.current_scope = enclosing

    def _visit_ReturnStatement(self, node):
        if self.function_depth == 0:
            raise SemanticError("'return' used outside of a function")
        if node.value is not None:
            self._visit(node.value)

    def _visit_Identifier(self, node):
        if not self.current_scope.is_defined(node.name):
            raise SemanticError("Undefined variable '" + node.name + "'")

    def _visit_IntLiteral(self, node):
        pass

    def _visit_FloatLiteral(self, node):
        pass

    def _visit_StringLiteral(self, node):
        pass

    def _visit_BoolLiteral(self, node):
        pass

    def _visit_UnaryExpr(self, node):
        self._visit(node.operand)

    def _visit_BinaryExpr(self, node):
        self._visit(node.left)
        self._visit(node.right)

    def _visit_AssignExpr(self, node):
        if not self.current_scope.is_defined(node.name):
            raise SemanticError("Cannot assign to undefined variable '" + node.name + "'")
        self._visit(node.value)

    def _visit_CallExpr(self, node):
        if node.callee in BUILTIN_FUNCTIONS:
            for arg in node.arguments:
                self._visit(arg)
            return

        if node.callee not in self.functions:
            raise SemanticError("Undefined function '" + node.callee + "'")

        expected = self.functions[node.callee]
        actual = len(node.arguments)
        if expected != actual:
            raise SemanticError("Function '" + node.callee + "' expects " + str(expected) + " argument(s), got " + str(actual))

        for arg in node.arguments:
            self._visit(arg)
# '@ | Set-Content -Path src\semantic\semantic_analyzer.py -Encoding UTF8