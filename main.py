
"""
MiniByte command-line entry point.

Usage:
    python main.py program.mb                    run a source file
    python main.py program.mb --compile          compile to program.mbc (binary bytecode)
    python main.py program.mb --compile -o x.mbc compile to a chosen file name
    python main.py program.mbc                   run a compiled bytecode file
    python main.py program.mb --hex              also print the binary bytecode as a hex dump
    python main.py program.mb --disasm           also print the readable instruction listing
    python main.py program.mb --vars             also print final variable values

Source file pipeline:
    lexer -> parser -> semantic analysis -> compiler -> bytecode -> VM
A .mbc file skips everything before the bytecode: it is loaded and run directly.
"""

import argparse
import os
import sys

from src.lexer.lexer import Lexer, LexerError
from src.parser.parser import Parser, ParserError
from src.semantic.semantic_analyzer import SemanticAnalyzer, SemanticError
from src.compiler.compiler import Compiler, CompilerError, disassemble
from src.compiler.bytecode import encode, decode, hexdump, BytecodeError, MAGIC
from src.vm.vm import VM, VMError


def compile_source(source):
    """Source text -> (instructions, functions). Prints an error and returns None on failure."""
    try:
        tokens = Lexer(source).tokenize()
    except LexerError as e:
        print("Syntax error (lexer): " + str(e), file=sys.stderr)
        return None

    try:
        program = Parser(tokens).parse()
    except ParserError as e:
        print("Syntax error (parser): " + str(e), file=sys.stderr)
        return None

    try:
        SemanticAnalyzer().analyze(program)
    except SemanticError as e:
        print("Semantic error: " + str(e), file=sys.stderr)
        return None

    try:
        return Compiler().compile(program)
    except CompilerError as e:
        print("Compiler error: " + str(e), file=sys.stderr)
        return None


def load_program(path):
    """Load a .mb source file or a .mbc bytecode file.

    The file type is detected from its first bytes, not its name.
    Returns (instructions, functions) or None after printing an error.
    """
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        print("Could not read file '" + path + "': " + str(e), file=sys.stderr)
        return None

    if data[:4] == MAGIC:
        try:
            return decode(data)
        except BytecodeError as e:
            print("Bytecode error: " + str(e), file=sys.stderr)
            return None

    try:
        # utf-8-sig also strips the invisible BOM some Windows tools add.
        source = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        print("'" + path + "' is neither MiniByte source text nor a bytecode file", file=sys.stderr)
        return None

    return compile_source(source)


def main():
    parser = argparse.ArgumentParser(
        prog="minibyte",
        description="Run, or compile, a MiniByte program (.mb source or .mbc bytecode).",
    )
    parser.add_argument("file", help="a .mb source file or a .mbc bytecode file")
    parser.add_argument("--compile", action="store_true",
                        help="write binary bytecode to a .mbc file instead of running")
    parser.add_argument("-o", "--output", help="output path for --compile")
    parser.add_argument("--hex", action="store_true",
                        help="print the binary bytecode as a hex dump")
    parser.add_argument("--disasm", action="store_true",
                        help="print the readable instruction listing")
    parser.add_argument("--vars", action="store_true",
                        help="print final global variable values after running")
    args = parser.parse_args()

    program = load_program(args.file)
    if program is None:
        sys.exit(1)
    instructions, functions = program

    if args.disasm:
        print("=== Bytecode listing ===")
        print(disassemble(instructions))
        if functions:
            print("\n=== Functions ===")
            for name, info in functions.items():
                address, arity = info
                print("  " + name + ": entry=" + str(address) + ", arity=" + str(arity))
        print()

    if args.hex or args.compile:
        try:
            data = encode(instructions, functions)
        except BytecodeError as e:
            print("Bytecode error: " + str(e), file=sys.stderr)
            sys.exit(1)

        if args.hex:
            print("=== Binary bytecode (" + str(len(data)) + " bytes) ===")
            print(hexdump(data))
            print()

        if args.compile:
            out_path = args.output or (os.path.splitext(args.file)[0] + ".mbc")
            try:
                with open(out_path, "wb") as f:
                    f.write(data)
            except OSError as e:
                print("Could not write '" + out_path + "': " + str(e), file=sys.stderr)
                sys.exit(1)
            print("Compiled " + str(len(instructions)) + " instructions to "
                  + out_path + " (" + str(len(data)) + " bytes)")
            return

    vm = VM(instructions, functions)
    try:
        vm.run()
    except VMError as e:
        print("Runtime error: " + str(e), file=sys.stderr)
        sys.exit(1)

    if args.vars:
        print("=== Global variables ===")
        for name, value in vm.global_vars.items():
            print("  " + name + " = " + repr(value))


if __name__ == "__main__":
    main()
# '@ | Set-Content -Path main.py -Encoding UTF8