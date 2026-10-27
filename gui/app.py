"""
MiniByte GUI - a simple PyQt6 editor/runner for MiniByte programs.

Run with:
    python gui/app.py
"""

import sys
import os
import io
import contextlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPlainTextEdit, QPushButton, QLabel, QSplitter, QTabWidget,
    QFileDialog, QMessageBox,
)
from PyQt6.QtGui import QFont, QTextCursor, QAction, QKeySequence
from PyQt6.QtCore import Qt

from src.lexer.lexer import Lexer, LexerError
from src.parser.parser import Parser, ParserError
from src.semantic.semantic_analyzer import SemanticAnalyzer, SemanticError
from src.compiler.compiler import Compiler, CompilerError, disassemble
from src.compiler.bytecode import encode, hexdump, BytecodeError
from src.vm.vm import VM, VMError


DEFAULT_PROGRAM = """// Welcome to MiniByte!
func add(a, b) {
    return a + b;
}

let x = 10;
let y = 25;
print("sum =", add(x, y));
"""


class MiniByteWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MiniByte Studio")
        self.resize(1000, 650)

        self.current_path = None

        self._build_ui()
        self._apply_style()
        self._set_status("Ready", "info")
        self.editor.setPlainText(DEFAULT_PROGRAM)

    def _apply_style(self):
        # VS Code "Dark+" inspired palette
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
            QPlainTextEdit {
                background-color: #0f172a;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                padding: 8px;
                selection-background-color: #264f78;
            }
            QPlainTextEdit#editorArea {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
            }
            QPushButton {
                background-color: #3a3d41;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #45494e;
            }
            QPushButton:pressed {
                background-color: #0e639c;
            }
            QTabWidget::pane {
                border: 1px solid #3c3c3c;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #969696;
                border: 1px solid #3c3c3c;
                border-bottom: none;
                padding: 6px 16px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #ffffff;
                border-bottom: 2px solid #007acc;
            }
            QTabBar::tab:hover {
                color: #d4d4d4;
            }
            QLabel#statusLabel {
                color: #cbd5e1;
                background-color: #1e293b;
                border-top: 1px solid #334155;
                padding: 2px 10px;
                font-size: 11px;
            }
            QMenuBar {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border-bottom: 1px solid #2d2d2d;
            }
            QMenuBar::item:selected {
                background-color: #505050;
            }
            QMenu {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #2d2d2d;
            }
            QMenu::item:selected {
                background-color: #007acc;
            }
            QSplitter::handle {
                background-color: #2d2d2d;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                background: #1e1e1e;
            }
            QScrollBar::handle {
                background: #424242;
                border-radius: 3px;
            }
            QScrollBar::handle:hover {
                background: #4f4f4f;
            }
        """)

    # ---------- UI construction ----------

    def _build_ui(self):
        mono = QFont("Consolas", 11)
        if not mono.exactMatch():
            mono = QFont("Courier New", 11)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)

        toolbar_layout = QHBoxLayout()
        self.run_button = QPushButton("Run  (Ctrl+Enter)")
        self.run_button.clicked.connect(self.run_program)
        self.assembly_button = QPushButton("Show Assembly")
        self.assembly_button.clicked.connect(self.show_assembly)
        self.bytecode_button = QPushButton("Show Bytecode")
        self.bytecode_button.clicked.connect(self.show_bytecode)
        self.clear_button = QPushButton("Clear Output")
        self.clear_button.clicked.connect(self.clear_output)
        toolbar_layout.addWidget(self.run_button)
        toolbar_layout.addWidget(self.assembly_button)
        toolbar_layout.addWidget(self.bytecode_button)
        toolbar_layout.addWidget(self.clear_button)
        toolbar_layout.addStretch()
        root_layout.addLayout(toolbar_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter)

        self.editor = QPlainTextEdit()
        self.editor.setObjectName("editorArea")
        self.editor.setFont(mono)
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        splitter.addWidget(self.editor)

        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)
        splitter.setSizes([550, 450])

        self.output_view = QPlainTextEdit()
        self.output_view.setReadOnly(True)
        self.output_view.setFont(mono)
        self.tabs.addTab(self.output_view, "Output")

        self.assembly_view = QPlainTextEdit()
        self.assembly_view.setReadOnly(True)
        self.assembly_view.setFont(mono)
        self.assembly_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.tabs.addTab(self.assembly_view, "Assembly Code")

        self.bytecode_view = QPlainTextEdit()
        self.bytecode_view.setReadOnly(True)
        self.bytecode_view.setFont(mono)
        self.bytecode_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.tabs.addTab(self.bytecode_view, "Bytecode")

        self.vars_view = QPlainTextEdit()
        self.vars_view.setReadOnly(True)
        self.vars_view.setFont(mono)
        self.tabs.addTab(self.vars_view, "Variables")

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setFixedHeight(22)
        root_layout.addWidget(self.status_label)

        run_action = QAction(self)
        run_action.setShortcut(QKeySequence("Ctrl+Return"))
        run_action.triggered.connect(self.run_program)
        self.addAction(run_action)

        self._build_menu()

    def _build_menu(self):
        menu = self.menuBar().addMenu("File")

        open_action = QAction("Open...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)
        menu.addAction(save_action)

        save_as_action = QAction("Save As...", self)
        save_as_action.triggered.connect(self.save_file_as)
        menu.addAction(save_as_action)

    # ---------- file operations ----------

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open MiniByte File", "", "MiniByte Files (*.mb);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.editor.setPlainText(f.read())
            self.current_path = path
            self.status_label.setText(f"Opened {path}")
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Could not open file:\n{e}")

    def save_file(self):
        if self.current_path is None:
            self.save_file_as()
            return
        self._write_to(self.current_path)

    def save_file_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save MiniByte File", "", "MiniByte Files (*.mb);;All Files (*)"
        )
        if not path:
            return
        self.current_path = path
        self._write_to(path)

    def _write_to(self, path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            self.status_label.setText(f"Saved {path}")
        except OSError as e:
            QMessageBox.critical(self, "Error", f"Could not save file:\n{e}")

    # ---------- run pipeline ----------

    def _set_status(self, text, kind="info"):
        # Subtle left accent bar instead of a full saturated block;
        # reads as a quiet IDE status line rather than a loud banner.
        accents = {
            "info": "#60a5fa",
            "success": "#4ade80",
            "error": "#f87171",
        }
        accent = accents.get(kind, accents["info"])
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            "background-color: #1e293b;"
            "color: #cbd5e1;"
            "border-top: 1px solid #334155;"
            f"border-left: 3px solid {accent};"
            "padding: 2px 10px;"
            "font-size: 11px;"
        )

    def clear_output(self):
        self.output_view.clear()
        self.assembly_view.clear()
        self.bytecode_view.clear()
        self.vars_view.clear()
        self._set_status("Ready", "info")

    def _append_output(self, text: str):
        self.output_view.moveCursor(QTextCursor.MoveOperation.End)
        self.output_view.insertPlainText(text)
        self.output_view.moveCursor(QTextCursor.MoveOperation.End)

    def _show_program(self, instructions, functions):
        """Fill the Assembly Code and Bytecode tabs for the program that just compiled."""
        self.assembly_view.setPlainText(disassemble(instructions))

        try:
            binary = encode(instructions, functions)
        except BytecodeError as e:
            self.bytecode_view.setPlainText("Could not encode bytecode: " + str(e))
            return

        self.bytecode_view.setPlainText(hexdump(binary, 8))

    def show_assembly(self):
        self.tabs.setCurrentWidget(self.assembly_view)

    def show_bytecode(self):
        self.tabs.setCurrentWidget(self.bytecode_view)

    def run_program(self):
        source = self.editor.toPlainText()
        self.output_view.clear()
        self.assembly_view.clear()
        self.bytecode_view.clear()
        self.vars_view.clear()
        self._set_status("Running...", "info")

        try:
            tokens = Lexer(source).tokenize()
        except LexerError as e:
            self._append_output(f"Syntax error (lexer): {e}\n")
            self._set_status("Failed: lexer error", "error")
            return

        try:
            program = Parser(tokens).parse()
        except ParserError as e:
            self._append_output(f"Syntax error (parser): {e}\n")
            self._set_status("Failed: parser error", "error")
            return

        if not program.statements:
            self._set_status("Nothing to run (the editor has no code)", "info")
            return

        try:
            SemanticAnalyzer().analyze(program)
        except SemanticError as e:
            self._append_output(f"Semantic error: {e}\n")
            self._set_status("Failed: semantic error", "error")
            return

        try:
            instructions, functions = Compiler().compile(program)
        except CompilerError as e:
            self._append_output(f"Compiler error: {e}\n")
            self._set_status("Failed: compiler error", "error")
            return

        self._show_program(instructions, functions)

        vm = VM(instructions, functions)
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                vm.run()
        except VMError as e:
            self._append_output(buffer.getvalue())
            self._append_output(f"\nRuntime error: {e}\n")
            self._set_status("Failed: runtime error", "error")
            return

        self._append_output(buffer.getvalue() or "(no output)\n")
        self._set_status("Finished successfully", "success")

        var_lines = [f"{name} = {value!r}" for name, value in vm.global_vars.items()]
        self.vars_view.setPlainText("\n".join(var_lines) if var_lines else "(no global variables)")


def main():
    app = QApplication(sys.argv)
    window = MiniByteWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()