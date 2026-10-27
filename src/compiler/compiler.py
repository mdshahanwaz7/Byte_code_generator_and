# @'
"""
Bytecode compiler for the MiniByte language.
"""

from src.parser.ast_nodes import (
    Program, LetStatement, ExpressionStatement, BlockStatement,
    IfStatement, WhileStatement, FunctionDef, ReturnStatement,
    Identifier, IntLiteral, FloatLiteral, StringLiteral, BoolLiteral,
    UnaryExpr, BinaryExpr, AssignExpr, CallExpr,
)
from src.compiler.opcodes import OpCode, Instruction


class CompilerError(Exception):
    pass


_BINARY_OPS = {
    "+": OpCode.ADD, "-": OpCode.SUB, "*": OpCode.MUL,
    "/": OpCode.DIV, "%": OpCode.MOD,
    "==": OpCode.EQ, "!=": OpCode.NEQ,
    "<": OpCode.LT, ">": OpCode.GT, "<=": OpCode.LTE, ">=": OpCode.GTE,
    "&&": OpCode.AND, "||": OpCode.OR,
}

_UNARY_OPS = {
    "-": OpCode.NEG,
    "!": OpCode.NOT,
}


class Compiler:
    def __init__(self):
        self.instructions = []
        self.functions = {}

    def compile(self, program):
        function_defs = [s for s in program.statements if isinstance(s, FunctionDef)]
        other_statements = [s for s in program.statements if not isinstance(s, FunctionDef)]

        jump_patch_index = None
        if function_defs:
            jump_patch_index = self._emit(OpCode.JUMP, None)
            for func in function_defs:
                self._compile_function(func)
            self._patch(jump_patch_index, len(self.instructions))

        for stmt in other_statements:
            self._compile_statement(stmt)

        self._emit(OpCode.HALT)
        return self.instructions, self.functions

    def _emit(self, opcode, arg=None):
        self.instructions.append(Instruction(opcode, arg))
        return len(self.instructions) - 1

    def _patch(self, index, target):
        self.instructions[index].arg = target

    def _compile_function(self, node):
        start_address = len(self.instructions)
        self.functions[node.name] = (start_address, len(node.params))

        for param in reversed(node.params):
            self._emit(OpCode.STORE_VAR, param)

        for stmt in node.body.statements:
            self._compile_statement(stmt)

        if not self.instructions or self.instructions[-1].opcode != OpCode.RETURN:
            self._emit(OpCode.PUSH_CONST, 0)
            self._emit(OpCode.RETURN)

    def _compile_statement(self, node):
        method_name = "_compile_" + type(node).__name__
        method = getattr(self, method_name, None)
        if method is None:
            raise CompilerError("No compiler rule for node type " + type(node).__name__)
        method(node)

    def _compile_LetStatement(self, node):
        self._compile_expression(node.value)
        self._emit(OpCode.STORE_VAR, node.name)

    def _compile_ExpressionStatement(self, node):
        self._compile_expression(node.expression)
        self._emit(OpCode.POP)

    def _compile_BlockStatement(self, node):
        for stmt in node.statements:
            self._compile_statement(stmt)

    def _compile_IfStatement(self, node):
        self._compile_expression(node.condition)
        else_jump = self._emit(OpCode.JUMP_IF_FALSE, None)

        self._compile_statement(node.then_branch)

        if node.else_branch is not None:
            end_jump = self._emit(OpCode.JUMP, None)
            self._patch(else_jump, len(self.instructions))
            self._compile_statement(node.else_branch)
            self._patch(end_jump, len(self.instructions))
        else:
            self._patch(else_jump, len(self.instructions))

    def _compile_WhileStatement(self, node):
        loop_start = len(self.instructions)
        self._compile_expression(node.condition)
        exit_jump = self._emit(OpCode.JUMP_IF_FALSE, None)

        self._compile_statement(node.body)
        self._emit(OpCode.JUMP, loop_start)

        self._patch(exit_jump, len(self.instructions))

    def _compile_ReturnStatement(self, node):
        if node.value is not None:
            self._compile_expression(node.value)
        else:
            self._emit(OpCode.PUSH_CONST, 0)
        self._emit(OpCode.RETURN)

    def _compile_expression(self, node):
        method_name = "_compile_expr_" + type(node).__name__
        method = getattr(self, method_name, None)
        if method is None:
            raise CompilerError("No compiler rule for expression type " + type(node).__name__)
        method(node)

    def _compile_expr_IntLiteral(self, node):
        self._emit(OpCode.PUSH_CONST, node.value)

    def _compile_expr_FloatLiteral(self, node):
        self._emit(OpCode.PUSH_CONST, node.value)

    def _compile_expr_StringLiteral(self, node):
        self._emit(OpCode.PUSH_CONST, node.value)

    def _compile_expr_BoolLiteral(self, node):
        self._emit(OpCode.PUSH_CONST, node.value)

    def _compile_expr_Identifier(self, node):
        self._emit(OpCode.LOAD_VAR, node.name)

    def _compile_expr_UnaryExpr(self, node):
        self._compile_expression(node.operand)
        opcode = _UNARY_OPS.get(node.operator)
        if opcode is None:
            raise CompilerError("Unknown unary operator '" + node.operator + "'")
        self._emit(opcode)

    def _compile_expr_BinaryExpr(self, node):
        self._compile_expression(node.left)
        self._compile_expression(node.right)
        opcode = _BINARY_OPS.get(node.operator)
        if opcode is None:
            raise CompilerError("Unknown binary operator '" + node.operator + "'")
        self._emit(opcode)

    def _compile_expr_AssignExpr(self, node):
        self._compile_expression(node.value)
        self._emit(OpCode.DUP)
        self._emit(OpCode.STORE_VAR, node.name)

    def _compile_expr_CallExpr(self, node):
        for arg in node.arguments:
            self._compile_expression(arg)

        if node.callee == "print":
            self._emit(OpCode.PRINT, len(node.arguments))
        else:
            self._emit(OpCode.CALL, (node.callee, len(node.arguments)))


def disassemble(instructions):
    lines = []
    for i, instr in enumerate(instructions):
        lines.append(str(i).rjust(4) + "  " + repr(instr))
    return "\n".join(lines)
# '@ | Set-Content -Path src\compiler\compiler.py -Encoding UTF8