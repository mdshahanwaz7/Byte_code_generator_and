# @'
"""
Stack-based virtual machine for MiniByte bytecode.
"""

from src.compiler.opcodes import OpCode


class VMError(Exception):
    pass


class CallFrame:
    __slots__ = ("return_address", "locals")

    def __init__(self, return_address):
        self.return_address = return_address
        self.locals = {}


def _truthy(value):
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return len(value) > 0
    return bool(value)


class VM:
    def __init__(self, instructions, functions):
        self.instructions = instructions
        self.functions = functions
        self.global_vars = {}
        self.call_stack = []
        self.stack = []
        self.pc = 0

    def run(self):
        while True:
            if self.pc >= len(self.instructions):
                raise VMError("Program counter ran past the end of the program")

            instr = self.instructions[self.pc]
            op = instr.opcode

            if op == OpCode.HALT:
                break
            elif op == OpCode.PUSH_CONST:
                self._push(instr.arg)
                self.pc += 1
            elif op == OpCode.POP:
                self._pop()
                self.pc += 1
            elif op == OpCode.DUP:
                self._push(self._peek())
                self.pc += 1
            elif op == OpCode.LOAD_VAR:
                self._push(self._load(instr.arg))
                self.pc += 1
            elif op == OpCode.STORE_VAR:
                self._store(instr.arg, self._pop())
                self.pc += 1
            elif op in self._BINARY_OPS:
                self._exec_binary(op)
                self.pc += 1
            elif op == OpCode.NEG:
                self._push(-self._pop())
                self.pc += 1
            elif op == OpCode.NOT:
                self._push(not _truthy(self._pop()))
                self.pc += 1
            elif op == OpCode.JUMP:
                self.pc = instr.arg
            elif op == OpCode.JUMP_IF_FALSE:
                if not _truthy(self._pop()):
                    self.pc = instr.arg
                else:
                    self.pc += 1
            elif op == OpCode.CALL:
                self._exec_call(instr.arg)
            elif op == OpCode.RETURN:
                self._exec_return()
            elif op == OpCode.PRINT:
                self._exec_print(instr.arg)
                self.pc += 1
            else:
                raise VMError("Unknown opcode " + str(op))

        return self.stack[-1] if self.stack else None

    def _push(self, value):
        self.stack.append(value)

    def _pop(self):
        if not self.stack:
            raise VMError("Stack underflow")
        return self.stack.pop()

    def _peek(self):
        if not self.stack:
            raise VMError("Stack underflow")
        return self.stack[-1]

    def _current_scope(self):
        return self.call_stack[-1].locals if self.call_stack else self.global_vars

    def _load(self, name):
        scope = self._current_scope()
        if name in scope:
            return scope[name]
        if scope is not self.global_vars and name in self.global_vars:
            return self.global_vars[name]
        raise VMError("Undefined variable '" + name + "'")

    def _store(self, name, value):
        self._current_scope()[name] = value

    _BINARY_OPS = {
        OpCode.ADD, OpCode.SUB, OpCode.MUL, OpCode.DIV, OpCode.MOD,
        OpCode.EQ, OpCode.NEQ, OpCode.LT, OpCode.GT, OpCode.LTE, OpCode.GTE,
        OpCode.AND, OpCode.OR,
    }

    def _exec_binary(self, op):
        right = self._pop()
        left = self._pop()

        if op == OpCode.ADD:
            if isinstance(left, str) or isinstance(right, str):
                self._push(str(left) + str(right))
            else:
                self._push(left + right)
        elif op == OpCode.SUB:
            self._push(left - right)
        elif op == OpCode.MUL:
            self._push(left * right)
        elif op == OpCode.DIV:
            if right == 0:
                raise VMError("Division by zero")
            self._push(left / right)
        elif op == OpCode.MOD:
            if right == 0:
                raise VMError("Modulo by zero")
            self._push(left % right)
        elif op == OpCode.EQ:
            self._push(left == right)
        elif op == OpCode.NEQ:
            self._push(left != right)
        elif op == OpCode.LT:
            self._push(left < right)
        elif op == OpCode.GT:
            self._push(left > right)
        elif op == OpCode.LTE:
            self._push(left <= right)
        elif op == OpCode.GTE:
            self._push(left >= right)
        elif op == OpCode.AND:
            self._push(_truthy(left) and _truthy(right))
        elif op == OpCode.OR:
            self._push(_truthy(left) or _truthy(right))

    def _exec_call(self, arg):
        name, arg_count = arg
        if name not in self.functions:
            raise VMError("Undefined function '" + name + "'")

        start_address, arity = self.functions[name]
        if arg_count != arity:
            raise VMError("Function '" + name + "' expects " + str(arity) + " argument(s), got " + str(arg_count))

        frame = CallFrame(return_address=self.pc + 1)
        self.call_stack.append(frame)
        self.pc = start_address

    def _exec_return(self):
        if not self.call_stack:
            raise VMError("'return' used with no active function call")
        return_value = self._pop()
        frame = self.call_stack.pop()
        self._push(return_value)
        self.pc = frame.return_address

    def _exec_print(self, arg_count):
        values = [self._pop() for _ in range(arg_count)]
        values.reverse()
        print(" ".join(self._format_value(v) for v in values))
        self._push(0)

    @staticmethod
    def _format_value(value):
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)
# '@ | Set-Content -Path src\vm\vm.py -Encoding UTF8