"""
Token type definitions for the MiniByte language.
"""

from enum import Enum, auto


class TokenType(Enum):
    # Literals
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    IDENTIFIER = auto()

    # Keywords
    LET = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FUNC = auto()
    RETURN = auto()
    TRUE = auto()
    FALSE = auto()

    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    ASSIGN = auto()         # =
    EQ = auto()              # ==
    NEQ = auto()             # !=
    LT = auto()               # <
    GT = auto()               # >
    LTE = auto()             # <=
    GTE = auto()             # >=
    AND = auto()             # &&
    OR = auto()               # ||
    NOT = auto()             # !

    # Punctuation
    LPAREN = auto()          # (
    RPAREN = auto()          # )
    LBRACE = auto()          # {
    RBRACE = auto()          # }
    COMMA = auto()           # ,
    SEMICOLON = auto()       # ;

    # Special
    EOF = auto()


KEYWORDS = {
    "let": TokenType.LET,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "func": TokenType.FUNC,
    "return": TokenType.RETURN,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
}