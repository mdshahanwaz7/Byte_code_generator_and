"""
Recursive-descent parser for the MiniByte language.

Consumes the token list produced by the lexer and builds an AST
(see ast_nodes.py). Operator precedence, lowest to highest:

    assignment
    ||
    &&
    == !=
    < > <= >=
    + -
    * / %
    unary (! -)
    primary
"""

from src.lexer.token_type import TokenType
from src.parser.ast_nodes import (
    Program, LetStatement, ExpressionStatement, BlockStatement,
    IfStatement, WhileStatement, FunctionDef, ReturnStatement,
    Identifier, IntLiteral, FloatLiteral, StringLiteral, BoolLiteral,
    UnaryExpr, BinaryExpr, AssignExpr, CallExpr,
)


class ParserError(Exception):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"Parser error at line {line}, column {column}: {message}")
        self.line = line
        self.column = column


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # ---------- public API ----------

    def parse(self) -> Program:
        statements = []
        while not self._check(TokenType.EOF):
            statements.append(self._statement())
        return Program(statements)

    # ---------- token helpers ----------

    def _peek(self):
        return self.tokens[self.pos]

    def _previous(self):
        return self.tokens[self.pos - 1]

    def _advance(self):
        if not self._check(TokenType.EOF):
            self.pos += 1
        return self._previous()

    def _check(self, type_: TokenType) -> bool:
        return self._peek().type == type_

    def _match(self, *types: TokenType) -> bool:
        if self._peek().type in types:
            self._advance()
            return True
        return False

    def _expect(self, type_: TokenType, message: str):
        if self._check(type_):
            return self._advance()
        tok = self._peek()
        raise ParserError(message, tok.line, tok.column)

    # ---------- statements ----------

    def _statement(self):
        if self._match(TokenType.LET):
            return self._let_statement()
        if self._match(TokenType.IF):
            return self._if_statement()
        if self._match(TokenType.WHILE):
            return self._while_statement()
        if self._match(TokenType.FUNC):
            return self._function_def()
        if self._match(TokenType.RETURN):
            return self._return_statement()
        if self._check(TokenType.LBRACE):
            return self._block()
        return self._expression_statement()

    def _let_statement(self):
        name_tok = self._expect(TokenType.IDENTIFIER, "Expected identifier after 'let'")
        self._expect(TokenType.ASSIGN, "Expected '=' after identifier in let statement")
        value = self._expression()
        self._expect(TokenType.SEMICOLON, "Expected ';' after let statement")
        return LetStatement(name_tok.value, value)

    def _if_statement(self):
        self._expect(TokenType.LPAREN, "Expected '(' after 'if'")
        condition = self._expression()
        self._expect(TokenType.RPAREN, "Expected ')' after if condition")
        then_branch = self._block()
        else_branch = None
        if self._match(TokenType.ELSE):
            if self._match(TokenType.IF):
                else_branch = self._if_statement()
            else:
                else_branch = self._block()
        return IfStatement(condition, then_branch, else_branch)

    def _while_statement(self):
        self._expect(TokenType.LPAREN, "Expected '(' after 'while'")
        condition = self._expression()
        self._expect(TokenType.RPAREN, "Expected ')' after while condition")
        body = self._block()
        return WhileStatement(condition, body)

    def _function_def(self):
        name_tok = self._expect(TokenType.IDENTIFIER, "Expected function name after 'func'")
        self._expect(TokenType.LPAREN, "Expected '(' after function name")
        params = []
        if not self._check(TokenType.RPAREN):
            params.append(self._expect(TokenType.IDENTIFIER, "Expected parameter name").value)
            while self._match(TokenType.COMMA):
                params.append(self._expect(TokenType.IDENTIFIER, "Expected parameter name").value)
        self._expect(TokenType.RPAREN, "Expected ')' after parameters")
        body = self._block()
        return FunctionDef(name_tok.value, params, body)

    def _return_statement(self):
        value = None
        if not self._check(TokenType.SEMICOLON):
            value = self._expression()
        self._expect(TokenType.SEMICOLON, "Expected ';' after return statement")
        return ReturnStatement(value)

    def _block(self):
        self._expect(TokenType.LBRACE, "Expected '{' to start block")
        statements = []
        while not self._check(TokenType.RBRACE) and not self._check(TokenType.EOF):
            statements.append(self._statement())
        self._expect(TokenType.RBRACE, "Expected '}' to close block")
        return BlockStatement(statements)

    def _expression_statement(self):
        expr = self._expression()
        self._expect(TokenType.SEMICOLON, "Expected ';' after expression")
        return ExpressionStatement(expr)

    # ---------- expressions (precedence climbing) ----------

    def _expression(self):
        return self._assignment()

    def _assignment(self):
        expr = self._logic_or()
        if self._match(TokenType.ASSIGN):
            equals_tok = self._previous()
            value = self._assignment()
            if isinstance(expr, Identifier):
                return AssignExpr(expr.name, value)
            raise ParserError("Invalid assignment target", equals_tok.line, equals_tok.column)
        return expr

    def _logic_or(self):
        expr = self._logic_and()
        while self._match(TokenType.OR):
            op = self._previous().value
            right = self._logic_and()
            expr = BinaryExpr(expr, op, right)
        return expr

    def _logic_and(self):
        expr = self._equality()
        while self._match(TokenType.AND):
            op = self._previous().value
            right = self._equality()
            expr = BinaryExpr(expr, op, right)
        return expr

    def _equality(self):
        expr = self._comparison()
        while self._match(TokenType.EQ, TokenType.NEQ):
            op = self._previous().value
            right = self._comparison()
            expr = BinaryExpr(expr, op, right)
        return expr

    def _comparison(self):
        expr = self._additive()
        while self._match(TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            op = self._previous().value
            right = self._additive()
            expr = BinaryExpr(expr, op, right)
        return expr

    def _additive(self):
        expr = self._multiplicative()
        while self._match(TokenType.PLUS, TokenType.MINUS):
            op = self._previous().value
            right = self._multiplicative()
            expr = BinaryExpr(expr, op, right)
        return expr

    def _multiplicative(self):
        expr = self._unary()
        while self._match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self._previous().value
            right = self._unary()
            expr = BinaryExpr(expr, op, right)
        return expr

    def _unary(self):
        if self._match(TokenType.NOT, TokenType.MINUS):
            op = self._previous().value
            operand = self._unary()
            return UnaryExpr(op, operand)
        return self._primary()

    def _primary(self):
        tok = self._peek()

        if self._match(TokenType.INT):
            return IntLiteral(self._previous().value)
        if self._match(TokenType.FLOAT):
            return FloatLiteral(self._previous().value)
        if self._match(TokenType.STRING):
            return StringLiteral(self._previous().value)
        if self._match(TokenType.TRUE):
            return BoolLiteral(True)
        if self._match(TokenType.FALSE):
            return BoolLiteral(False)

        if self._match(TokenType.IDENTIFIER):
            name = self._previous().value
            if self._match(TokenType.LPAREN):
                args = []
                if not self._check(TokenType.RPAREN):
                    args.append(self._expression())
                    while self._match(TokenType.COMMA):
                        args.append(self._expression())
                self._expect(TokenType.RPAREN, "Expected ')' after arguments")
                return CallExpr(name, args)
            return Identifier(name)

        if self._match(TokenType.LPAREN):
            expr = self._expression()
            self._expect(TokenType.RPAREN, "Expected ')' after expression")
            return expr

        raise ParserError(f"Unexpected token {tok.type}", tok.line, tok.column)