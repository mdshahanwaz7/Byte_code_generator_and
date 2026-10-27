"""
Lexer (tokenizer) for the MiniByte language.

Turns raw source text into a flat list of Token objects that the
parser (Step 6) will consume.
"""

from src.lexer.token import Token
from src.lexer.token_type import TokenType, KEYWORDS


class LexerError(Exception):
    """Raised when the lexer encounters invalid source text."""

    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"Lexer error at line {line}, column {column}: {message}")
        self.line = line
        self.column = column


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []

    # ---------- public API ----------

    def tokenize(self):
        while not self._at_end():
            self._skip_whitespace_and_comments()
            if self._at_end():
                break
            start_line, start_col = self.line, self.column
            ch = self._advance()

            if ch.isdigit():
                self._number(start_line, start_col)
            elif ch.isalpha() or ch == "_":
                self._identifier_or_keyword(start_line, start_col)
            elif ch == '"':
                self._string(start_line, start_col)
            else:
                self._operator_or_punctuation(ch, start_line, start_col)

        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return self.tokens

    # ---------- character helpers ----------

    def _at_end(self) -> bool:
        return self.pos >= len(self.source)

    def _peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        if idx >= len(self.source):
            return "\0"
        return self.source[idx]

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _match(self, expected: str) -> bool:
        if self._peek() == expected:
            self._advance()
            return True
        return False

    def _skip_whitespace_and_comments(self):
        while not self._at_end():
            ch = self._peek()
            if ch in " \t\r\n":
                self._advance()
            elif ch == "/" and self._peek(1) == "/":
                # line comment: skip to end of line
                while not self._at_end() and self._peek() != "\n":
                    self._advance()
            else:
                break

    # ---------- token builders ----------

    def _add(self, type_: TokenType, value, line: int, column: int):
        self.tokens.append(Token(type_, value, line, column))

    def _number(self, line: int, col: int):
        start = self.pos - 1
        is_float = False

        while self._peek().isdigit():
            self._advance()

        if self._peek() == "." and self._peek(1).isdigit():
            is_float = True
            self._advance()  # consume '.'
            while self._peek().isdigit():
                self._advance()

        text = self.source[start:self.pos]
        if is_float:
            self._add(TokenType.FLOAT, float(text), line, col)
        else:
            self._add(TokenType.INT, int(text), line, col)

    def _identifier_or_keyword(self, line: int, col: int):
        start = self.pos - 1
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()

        text = self.source[start:self.pos]
        token_type = KEYWORDS.get(text, TokenType.IDENTIFIER)
        self._add(token_type, text, line, col)

    def _string(self, line: int, col: int):
        start = self.pos
        while not self._at_end() and self._peek() != '"':
            if self._peek() == "\n":
                raise LexerError("Unterminated string literal", line, col)
            self._advance()

        if self._at_end():
            raise LexerError("Unterminated string literal", line, col)

        text = self.source[start:self.pos]
        self._advance()  # consume closing quote
        self._add(TokenType.STRING, text, line, col)

    def _operator_or_punctuation(self, ch: str, line: int, col: int):
        simple = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.SLASH,
            "%": TokenType.PERCENT,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            ",": TokenType.COMMA,
            ";": TokenType.SEMICOLON,
        }

        if ch == "=":
            self._add(TokenType.EQ if self._match("=") else TokenType.ASSIGN, ch, line, col)
        elif ch == "!":
            self._add(TokenType.NEQ if self._match("=") else TokenType.NOT, ch, line, col)
        elif ch == "<":
            self._add(TokenType.LTE if self._match("=") else TokenType.LT, ch, line, col)
        elif ch == ">":
            self._add(TokenType.GTE if self._match("=") else TokenType.GT, ch, line, col)
        elif ch == "&" and self._match("&"):
            self._add(TokenType.AND, "&&", line, col)
        elif ch == "|" and self._match("|"):
            self._add(TokenType.OR, "||", line, col)
        elif ch in simple:
            self._add(simple[ch], ch, line, col)
        else:
            raise LexerError(f"Unexpected character {ch!r}", line, col)