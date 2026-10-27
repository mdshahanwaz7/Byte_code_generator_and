"""
AST node definitions for the MiniByte language.

Each node is a plain data container (no behavior) that represents a
piece of program structure. The parser builds these; later stages
(semantic analysis, bytecode compiler) walk them.
"""


class Node:
    """Base class for all AST nodes."""
    def __repr__(self):
        fields = ", ".join(f"{k}={v!r}" for k, v in vars(self).items())
        return f"{self.__class__.__name__}({fields})"

    def __eq__(self, other):
        return isinstance(other, self.__class__) and vars(self) == vars(other)


# ---------- Program ----------

class Program(Node):
    def __init__(self, statements):
        self.statements = statements


# ---------- Statements ----------

class LetStatement(Node):
    def __init__(self, name, value):
        self.name = name        # str
        self.value = value      # Expr


class ExpressionStatement(Node):
    def __init__(self, expression):
        self.expression = expression


class BlockStatement(Node):
    def __init__(self, statements):
        self.statements = statements


class IfStatement(Node):
    def __init__(self, condition, then_branch, else_branch=None):
        self.condition = condition          # Expr
        self.then_branch = then_branch      # BlockStatement
        self.else_branch = else_branch      # BlockStatement | IfStatement | None


class WhileStatement(Node):
    def __init__(self, condition, body):
        self.condition = condition      # Expr
        self.body = body                # BlockStatement


class FunctionDef(Node):
    def __init__(self, name, params, body):
        self.name = name          # str
        self.params = params      # list[str]
        self.body = body          # BlockStatement


class ReturnStatement(Node):
    def __init__(self, value):
        self.value = value      # Expr | None


# ---------- Expressions ----------

class Identifier(Node):
    def __init__(self, name):
        self.name = name


class IntLiteral(Node):
    def __init__(self, value):
        self.value = value


class FloatLiteral(Node):
    def __init__(self, value):
        self.value = value


class StringLiteral(Node):
    def __init__(self, value):
        self.value = value


class BoolLiteral(Node):
    def __init__(self, value):
        self.value = value


class UnaryExpr(Node):
    def __init__(self, operator, operand):
        self.operator = operator      # str, e.g. '-', '!'
        self.operand = operand        # Expr


class BinaryExpr(Node):
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator      # str, e.g. '+', '==', '&&'
        self.right = right


class AssignExpr(Node):
    def __init__(self, name, value):
        self.name = name          # str
        self.value = value        # Expr


class CallExpr(Node):
    def __init__(self, callee, arguments):
        self.callee = callee            # str (function name)
        self.arguments = arguments      # list[Expr]