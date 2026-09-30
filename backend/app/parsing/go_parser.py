"""
Repository Intelligence Engine — Tree-sitter Go Parser
Extracts structs, interfaces, functions, methods, imports, and calls
from Go source files using tree-sitter.
"""

from __future__ import annotations

from typing import Any

import tree_sitter_go as tsgo
from tree_sitter import Language
from tree_sitter import Parser as TSParser

from app.core.logging import get_logger
from app.parsing.base import (
    ParsedCall,
    ParsedImport,
    ParsedSymbol,
    Parser,
    ParseResult,
)

log = get_logger(__name__)

GO_LANGUAGE = Language(tsgo.language())


class TreeSitterGoParser(Parser):
    """Parser for Go source files using tree-sitter."""

    def __init__(self):
        self._parser = TSParser(GO_LANGUAGE)

    @property
    def supported_extensions(self) -> list[str]:
        return [".go"]

    @property
    def language_name(self) -> str:
        return "Go"

    def parse(self, file_path: str, source_code: str) -> ParseResult:
        tree = self._parser.parse(source_code.encode("utf-8"))
        root = tree.root_node

        symbols: list[ParsedSymbol] = []
        imports: list[ParsedImport] = []
        calls: list[ParsedCall] = []

        self._walk_tree(root, source_code, file_path, symbols, imports, calls)

        lines_of_code = len([line for line in source_code.splitlines() if line.strip()])

        return ParseResult(
            file_path=file_path,
            language="Go",
            symbols=symbols,
            imports=imports,
            calls=calls,
            lines_of_code=lines_of_code,
        )

    def _walk_tree(
        self,
        node: Any,
        source: str,
        file_path: str,
        symbols: list[ParsedSymbol],
        imports: list[ParsedImport],
        calls: list[ParsedCall],
        parent_name: str | None = None,
    ) -> None:
        if node.type == "import_declaration":
            self._extract_imports(node, source, imports)
            return

        elif node.type == "type_declaration":
            self._extract_types(node, source, file_path, symbols)
            return

        elif node.type == "function_declaration":
            sym = self._extract_function(node, source, file_path)
            if sym:
                symbols.append(sym)
                body = node.child_by_field_name("body")
                if body:
                    self._extract_calls(body, source, file_path, sym.name, calls)
            return

        elif node.type == "method_declaration":
            sym = self._extract_method(node, source, file_path)
            if sym:
                symbols.append(sym)
                body = node.child_by_field_name("body")
                if body:
                    caller_name = f"{sym.parent}.{sym.name}" if sym.parent else sym.name
                    self._extract_calls(body, source, file_path, caller_name, calls)
            return

        for child in node.children:
            self._walk_tree(child, source, file_path, symbols, imports, calls, parent_name)

    def _extract_imports(self, node: Any, source: str, imports: list[ParsedImport]) -> None:
        """Extract import statements from import_declaration."""
        for child in node.children:
            if child.type == "import_spec":
                path_node = child.child_by_field_name("path") or child.children[-1]
                mod_path = path_node.text.decode("utf-8").strip("\"'")
                alias_node = child.child_by_field_name("name")
                alias = alias_node.text.decode("utf-8") if alias_node else None
                is_rel = mod_path.startswith(".") or "/" not in mod_path
                imports.append(
                    ParsedImport(
                        module=mod_path,
                        alias=alias,
                        is_relative=is_rel,
                        line_number=child.start_point[0] + 1,
                    )
                )
            elif child.type == "import_spec_list":
                for spec in child.children:
                    if spec.type == "import_spec":
                        path_node = spec.child_by_field_name("path") or spec.children[-1]
                        mod_path = path_node.text.decode("utf-8").strip("\"'")
                        alias_node = spec.child_by_field_name("name")
                        alias = alias_node.text.decode("utf-8") if alias_node else None
                        is_rel = mod_path.startswith(".")
                        imports.append(
                            ParsedImport(
                                module=mod_path,
                                alias=alias,
                                is_relative=is_rel,
                                line_number=spec.start_point[0] + 1,
                            )
                        )

    def _extract_types(self, node: Any, source: str, file_path: str, symbols: list[ParsedSymbol]) -> None:
        """Extract structs, interfaces, and type aliases from type_declaration."""
        for child in node.children:
            if child.type == "type_spec":
                name_node = child.child_by_field_name("name")
                if not name_node:
                    continue
                name = name_node.text.decode("utf-8")
                type_node = child.child_by_field_name("type")
                sym_type = "class"
                if type_node and type_node.type == "interface_type":
                    sym_type = "interface"
                elif type_node and type_node.type == "struct_type":
                    sym_type = "class"

                visibility = "public" if name[0].isupper() else "private"
                signature = child.text.decode("utf-8").split("{")[0].strip()

                symbols.append(
                    ParsedSymbol(
                        name=name,
                        type=sym_type,
                        file_path=file_path,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                        signature=signature,
                        visibility=visibility,
                    )
                )

    def _extract_function(self, node: Any, source: str, file_path: str) -> ParsedSymbol | None:
        """Extract top-level function declaration."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None
        name = name_node.text.decode("utf-8")
        visibility = "public" if name[0].isupper() else "private"

        params = []
        param_node = node.child_by_field_name("parameters")
        if param_node:
            for p in param_node.children:
                if p.type == "parameter_declaration":
                    p_name = p.child_by_field_name("name")
                    p_type = p.child_by_field_name("type")
                    if p_name and p_type:
                        params.append({
                            "name": p_name.text.decode("utf-8"),
                            "type": p_type.text.decode("utf-8"),
                        })

        ret_node = node.child_by_field_name("result")
        return_type = ret_node.text.decode("utf-8") if ret_node else None

        sig_lines = node.text.decode("utf-8").split("{")[0].strip()

        return ParsedSymbol(
            name=name,
            type="function",
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            signature=sig_lines,
            parameters=params,
            return_type=return_type,
            visibility=visibility,
        )

    def _extract_method(self, node: Any, source: str, file_path: str) -> ParsedSymbol | None:
        """Extract method declaration with receiver type."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None
        name = name_node.text.decode("utf-8")
        visibility = "public" if name[0].isupper() else "private"

        # Determine receiver parent type
        parent = None
        receiver_node = node.child_by_field_name("receiver")
        if receiver_node:
            for child in receiver_node.children:
                if child.type == "parameter_declaration":
                    type_node = child.child_by_field_name("type")
                    if type_node:
                        # Clean pointer e.g. *Server -> Server
                        parent = type_node.text.decode("utf-8").lstrip("*")

        ret_node = node.child_by_field_name("result")
        return_type = ret_node.text.decode("utf-8") if ret_node else None
        sig_lines = node.text.decode("utf-8").split("{")[0].strip()

        return ParsedSymbol(
            name=name,
            type="method",
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            signature=sig_lines,
            parent=parent,
            return_type=return_type,
            visibility=visibility,
        )

    def _extract_calls(
        self,
        node: Any,
        source: str,
        file_path: str,
        caller: str,
        calls: list[ParsedCall],
    ) -> None:
        """Recursively extract function and method calls inside body."""
        if node.type == "call_expression":
            fn_node = node.child_by_field_name("function")
            if fn_node:
                callee = fn_node.text.decode("utf-8")
                calls.append(
                    ParsedCall(
                        caller=caller,
                        callee=callee,
                        line_number=node.start_point[0] + 1,
                        file_path=file_path,
                    )
                )

        for child in node.children:
            self._extract_calls(child, source, file_path, caller, calls)
