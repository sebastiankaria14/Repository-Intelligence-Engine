"""
Repository Intelligence Engine — Tree-sitter Java Parser
Extracts classes, interfaces, methods, fields, imports, and call
relationships from Java source files.
"""

from __future__ import annotations

from typing import Any

import tree_sitter_java as tsjava
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

JAVA_LANGUAGE = Language(tsjava.language())


class TreeSitterJavaParser(Parser):
    """Parser for Java source files using tree-sitter."""

    def __init__(self):
        self._parser = TSParser(JAVA_LANGUAGE)

    @property
    def supported_extensions(self) -> list[str]:
        return [".java"]

    @property
    def language_name(self) -> str:
        return "Java"

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
            language="Java",
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
        if node.type in ("class_declaration", "enum_declaration", "record_declaration"):
            sym = self._extract_class(node, source, file_path, parent_name)
            if sym:
                symbols.append(sym)
                body = self._child_by_field(node, "body")
                if body:
                    self._walk_tree(body, source, file_path, symbols, imports, calls, parent_name=sym.name)
                return

        elif node.type == "interface_declaration":
            sym = self._extract_interface(node, source, file_path, parent_name)
            if sym:
                symbols.append(sym)
                body = self._child_by_field(node, "body")
                if body:
                    self._walk_tree(body, source, file_path, symbols, imports, calls, parent_name=sym.name)
                return

        elif node.type in ("method_declaration", "constructor_declaration"):
            sym = self._extract_method(node, source, file_path, parent_name)
            if sym:
                symbols.append(sym)
                body = self._child_by_field(node, "body")
                if body:
                    self._extract_calls_recursive(body, source, file_path, sym.name, calls)
                return

        elif node.type == "field_declaration":
            syms = self._extract_field(node, source, file_path, parent_name)
            symbols.extend(syms)

        elif node.type == "import_declaration":
            imp = self._extract_import(node, source)
            if imp:
                imports.append(imp)

        for child in node.children:
            self._walk_tree(child, source, file_path, symbols, imports, calls, parent_name)

    def _extract_class(self, node: Any, source: str, file_path: str, parent: str | None) -> ParsedSymbol | None:
        name_node = self._child_by_field(node, "name")
        if not name_node:
            return None
        name = self._text(name_node, source)

        # Get modifiers (public, private, abstract, etc.)
        visibility = self._get_visibility(node, source)

        # Get implemented interfaces and superclass
        annotations = []
        superclass = self._child_by_field(node, "superclass")
        if superclass:
            ext = self._text(superclass, source)
            annotations.append(ext if ext.startswith("extends ") else f"extends {ext}")
        interfaces = self._child_by_field(node, "interfaces")
        if interfaces:
            imp = self._text(interfaces, source)
            annotations.append(imp if imp.startswith("implements ") else f"implements {imp}")

        # Get decorators (annotations)
        decorators = self._get_annotations(node, source)

        return ParsedSymbol(
            name=name,
            type="class",
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            parent=parent,
            decorators=decorators,
            annotations=annotations,
            visibility=visibility,
        )

    def _extract_interface(self, node: Any, source: str, file_path: str, parent: str | None) -> ParsedSymbol | None:
        name_node = self._child_by_field(node, "name")
        if not name_node:
            return None
        return ParsedSymbol(
            name=self._text(name_node, source),
            type="interface",
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            parent=parent,
            decorators=self._get_annotations(node, source),
            visibility=self._get_visibility(node, source),
        )

    def _extract_method(self, node: Any, source: str, file_path: str, parent: str | None) -> ParsedSymbol | None:
        name_node = self._child_by_field(node, "name")
        if not name_node:
            return None
        name = self._text(name_node, source)

        params_node = self._child_by_field(node, "parameters")
        parameters = self._extract_params(params_node, source) if params_node else []

        return_type_node = self._child_by_field(node, "type")
        return_type = self._text(return_type_node, source) if return_type_node else None

        visibility = self._get_visibility(node, source)
        decorators = self._get_annotations(node, source)

        sig_params = self._text(params_node, source) if params_node else "()"
        ret = return_type or "void"
        signature = f"{ret} {name}{sig_params}"

        return ParsedSymbol(
            name=name,
            type="method",
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            signature=signature,
            parent=parent,
            parameters=parameters,
            return_type=return_type,
            visibility=visibility,
            decorators=decorators,
        )

    def _extract_field(self, node: Any, source: str, file_path: str, parent: str | None) -> list[ParsedSymbol]:
        """Extract field declarations."""
        symbols: list[ParsedSymbol] = []
        for child in node.children:
            if child.type == "variable_declarator":
                name_node = self._child_by_field(child, "name")
                if name_node:
                    symbols.append(ParsedSymbol(
                        name=self._text(name_node, source),
                        type="variable",
                        file_path=file_path,
                        line_start=node.start_point[0] + 1,
                        line_end=node.end_point[0] + 1,
                        parent=parent,
                        visibility=self._get_visibility(node, source),
                    ))
        return symbols

    def _extract_import(self, node: Any, source: str) -> ParsedImport | None:
        text = self._text(node, source).strip().rstrip(";")
        # Remove 'import' and optional 'static'
        text = text.replace("import static ", "").replace("import ", "")
        if not text:
            return None

        parts = text.rsplit(".", 1)
        module = parts[0] if len(parts) > 1 else text
        name = parts[1] if len(parts) > 1 else None

        return ParsedImport(
            module=module,
            name=name,
            line_number=node.start_point[0] + 1,
        )

    def _extract_calls_recursive(
        self, node: Any, source: str, file_path: str, caller: str, calls: list[ParsedCall],
    ) -> None:
        if node.type == "method_invocation":
            method_name = self._child_by_field(node, "name")
            obj = self._child_by_field(node, "object")
            if method_name:
                callee_parts = []
                if obj:
                    callee_parts.append(self._text(obj, source))
                callee_parts.append(self._text(method_name, source))
                calls.append(ParsedCall(
                    caller=caller,
                    callee=".".join(callee_parts),
                    line_number=node.start_point[0] + 1,
                    file_path=file_path,
                ))

        elif node.type == "object_creation_expression":
            type_node = self._child_by_field(node, "type")
            if type_node:
                calls.append(ParsedCall(
                    caller=caller,
                    callee=f"new {self._text(type_node, source)}",
                    line_number=node.start_point[0] + 1,
                    file_path=file_path,
                ))

        for child in node.children:
            self._extract_calls_recursive(child, source, file_path, caller, calls)

    def _extract_params(self, params_node: Any, source: str) -> list[dict[str, str]]:
        params: list[dict[str, str]] = []
        if not params_node:
            return params
        for child in params_node.children:
            if child.type in ("formal_parameter", "spread_parameter"):
                name_node = self._child_by_field(child, "name")
                type_node = self._child_by_field(child, "type")
                if name_node:
                    entry: dict[str, str] = {"name": self._text(name_node, source)}
                    if type_node:
                        entry["type"] = self._text(type_node, source)
                    params.append(entry)
        return params

    def _get_visibility(self, node: Any, source: str) -> str:
        for child in node.children:
            if child.type == "modifiers":
                text = self._text(child, source).lower()
                if "private" in text:
                    return "private"
                if "protected" in text:
                    return "protected"
                if "public" in text:
                    return "public"
        return "package"  # Java default

    def _get_annotations(self, node: Any, source: str) -> list[str]:
        annotations: list[str] = []
        for child in node.children:
            if child.type == "modifiers":
                for mod_child in child.children:
                    if mod_child.type in ("marker_annotation", "annotation"):
                        annotations.append(self._text(mod_child, source))
        return annotations

    def _child_by_field(self, node: Any, field_name: str) -> Any | None:
        return node.child_by_field_name(field_name)

    def _text(self, node: Any, source: str) -> str:
        return source[node.start_byte:node.end_byte]
