"""
Repository Intelligence Engine — Tree-sitter Rust Parser
Extracts structs, enums, traits, impl methods, functions, use declarations,
and call relationships from Rust source files using tree-sitter.
"""

from __future__ import annotations

from typing import Any

import tree_sitter_rust as tsrust
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

RUST_LANGUAGE = Language(tsrust.language())


class TreeSitterRustParser(Parser):
    """Parser for Rust source files using tree-sitter."""

    def __init__(self):
        self._parser = TSParser(RUST_LANGUAGE)

    @property
    def supported_extensions(self) -> list[str]:
        return [".rs"]

    @property
    def language_name(self) -> str:
        return "Rust"

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
            language="Rust",
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
        if node.type == "use_declaration":
            self._extract_use(node, source, imports)
            return

        elif node.type == "struct_item":
            sym = self._extract_struct(node, source, file_path)
            if sym:
                symbols.append(sym)
            return

        elif node.type == "enum_item":
            sym = self._extract_enum(node, source, file_path)
            if sym:
                symbols.append(sym)
            return

        elif node.type == "trait_item":
            sym = self._extract_trait(node, source, file_path)
            if sym:
                symbols.append(sym)
            return

        elif node.type == "impl_item":
            self._extract_impl(node, source, file_path, symbols, calls)
            return

        elif node.type == "function_item":
            sym = self._extract_function(node, source, file_path, parent_name=parent_name)
            if sym:
                symbols.append(sym)
                body = node.child_by_field_name("body")
                if body:
                    caller = f"{parent_name}::{sym.name}" if parent_name else sym.name
                    self._extract_calls(body, source, file_path, caller, calls)
            return

        for child in node.children:
            self._walk_tree(child, source, file_path, symbols, imports, calls, parent_name)

    def _extract_use(self, node: Any, source: str, imports: list[ParsedImport]) -> None:
        """Extract use statement (module import)."""
        arg_node = node.child_by_field_name("argument")
        if not arg_node:
            # Fallback to second child (after 'use')
            arg_node = node.children[1] if len(node.children) > 1 else None

        if arg_node:
            raw_text = arg_node.text.decode("utf-8").rstrip(";")
            is_rel = raw_text.startswith("crate::") or raw_text.startswith("super::") or raw_text.startswith("self::")
            imports.append(
                ParsedImport(
                    module=raw_text,
                    is_relative=is_rel,
                    line_number=node.start_point[0] + 1,
                )
            )

    def _extract_struct(self, node: Any, source: str, file_path: str) -> ParsedSymbol | None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None
        name = name_node.text.decode("utf-8")
        vis = self._get_visibility(node)
        sig = node.text.decode("utf-8").split("{")[0].strip()

        return ParsedSymbol(
            name=name,
            type="class",
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            signature=sig,
            visibility=vis,
        )

    def _extract_enum(self, node: Any, source: str, file_path: str) -> ParsedSymbol | None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None
        name = name_node.text.decode("utf-8")
        vis = self._get_visibility(node)
        sig = node.text.decode("utf-8").split("{")[0].strip()

        return ParsedSymbol(
            name=name,
            type="class",
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            signature=sig,
            visibility=vis,
        )

    def _extract_trait(self, node: Any, source: str, file_path: str) -> ParsedSymbol | None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None
        name = name_node.text.decode("utf-8")
        vis = self._get_visibility(node)
        sig = node.text.decode("utf-8").split("{")[0].strip()

        return ParsedSymbol(
            name=name,
            type="interface",
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            signature=sig,
            visibility=vis,
        )

    def _extract_impl(
        self,
        node: Any,
        source: str,
        file_path: str,
        symbols: list[ParsedSymbol],
        calls: list[ParsedCall],
    ) -> None:
        """Extract methods from impl Type or impl Trait for Type blocks."""
        type_node = node.child_by_field_name("type")
        trait_node = node.child_by_field_name("trait")

        type_name = type_node.text.decode("utf-8") if type_node else "Unknown"
        trait_name = trait_node.text.decode("utf-8") if trait_node else None

        body_node = node.child_by_field_name("body")
        if not body_node:
            return

        for child in body_node.children:
            if child.type == "function_item":
                sym = self._extract_function(child, source, file_path, parent_name=type_name)
                if sym:
                    sym.type = "method"
                    if trait_name:
                        sym.metadata["implements_trait"] = trait_name
                    symbols.append(sym)

                    fn_body = child.child_by_field_name("body")
                    if fn_body:
                        caller = f"{type_name}::{sym.name}"
                        self._extract_calls(fn_body, source, file_path, caller, calls)

    def _extract_function(
        self,
        node: Any,
        source: str,
        file_path: str,
        parent_name: str | None = None,
    ) -> ParsedSymbol | None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None
        name = name_node.text.decode("utf-8")
        vis = self._get_visibility(node)

        ret_node = node.child_by_field_name("return_type")
        return_type = ret_node.text.decode("utf-8") if ret_node else None

        sig = node.text.decode("utf-8").split("{")[0].strip()

        return ParsedSymbol(
            name=name,
            type="method" if parent_name else "function",
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            signature=sig,
            parent=parent_name,
            return_type=return_type,
            visibility=vis,
        )

    def _get_visibility(self, node: Any) -> str:
        for child in node.children:
            if child.type == "visibility_modifier":
                return "public"
        return "private"

    def _extract_calls(
        self,
        node: Any,
        source: str,
        file_path: str,
        caller: str,
        calls: list[ParsedCall],
    ) -> None:
        """Extract function/method calls and macro invocations."""
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

        elif node.type == "macro_invocation":
            macro_node = node.child_by_field_name("macro")
            if macro_node:
                callee = macro_node.text.decode("utf-8") + "!"
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
