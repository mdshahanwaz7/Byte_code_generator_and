"""
Token representation for the MiniByte language.
"""

from src.lexer.token_type import TokenType


class Token:
    __slots__ = ("type", "value", "line", "column")

    def __init__(self, type_: TokenType, value, line: int, column: int):
        self.type = type_
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line}, col={self.column})"

    def __eq__(self, other):
        if not isinstance(other, Token):
            return NotImplemented
        return (
            self.type == other.type
            and self.value == other.value
            and self.line == other.line
            and self.column == other.column
        )