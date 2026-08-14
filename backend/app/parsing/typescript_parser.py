"""
Repository Intelligence Engine — Tree-sitter TypeScript / JavaScript Parser
Extracts classes, interfaces, enums, type aliases, functions/methods, fields,
imports, decorators and call relationships from TypeScript and JavaScript
source files using the tree-sitter TS/JS grammar.
"""

from __future__ import annotations

from typing import Any

import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts
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

JS_LANGUAGE = Language(tsjs.language())
TS_LANGUAGE = Language(tsts.language_typescript())

_TS_EXTS = (".ts", ".tsx")
_DEFINITION_TYPES = (
    "class_declaration",
    "abstract_class_declaration",
    "interface_declaration",
    "enum_declaration",
    "type_alias_declaration",
    "function_declaration",
    "method_definition",
)
_MODIFIER_TOKENS = {"static", "abstract", "readonly", "async", "declare"}


class TreeSitterTSJSParser(Parser):
    """Parser for TypeScript and JavaScript source files using tree-sitter."""

    def __init__(self):
        self._js_parser = TSParser(JS_LANGUAGE)
        self._ts_parser = TSParser(TS_LANGUAGE)

    @property
    def supported_extensions(self) -> list[str]:
        return [".ts", ".tsx", ".js", ".jsx"]

    @property
    def language_name(self) -> str:
        return "TypeScript/JavaScript"

    def parse(self, file_path: str, source_code: str) -> ParseResult:
        is_ts = file_path.endswith(_TS_EXTS)
        parser = self._ts_parser if is_ts else self._js_parser
        language = "TypeScript" if is_ts else "JavaScript"

        tree = parser.parse(source_code.encode("utf-8"))
        root = tree.root_node

        symbols: list[ParsedSymbol] = []
        imports: list[ParsedImport] = []
        calls: list[ParsedCall] = []

        self._walk(
            root, source_code, file_path, symbols, imports, calls,
            parent=None, in_class=False, caller=None,
        )

        lines_of_code = len([line for line in source_code.splitlines() if line.strip()])

        return ParseResult(
            file_path=file_path,
            language=language,
            symbols=symbols,
            imports=imports,
            calls=calls,
            lines_of_code=lines_of_code,
        )

    def _walk(
        self,
        node: Any,
        source: str,
        file_path: str,
        symbols: list[ParsedSymbol],
        imports: list[ParsedImport],
        calls: list[ParsedCall],
        parent: str | None,
        in_class: bool,
        caller: str | None,
    ) -> None:
        t = node.type

        if t == "import_statement":
            imports.extend(self._extract_imports(node, source))

        elif t in _DEFINITION_TYPES:
            self._process_definition(
                node, source, file_path, symbols, imports, calls, parent, in_class, caller,
            )
            return

        elif t in ("field_definition", "public_field_definition"):
            sym = self._extract_field(node, source, file_path, parent)
            if sym:
                symbols.append(sym)
            return

        elif t == "call_expression":
            if caller:
                callee = self._field_text(node, "function", source)
                if callee:
                    calls.append(ParsedCall(
                        caller=caller, callee=callee,
                        line_number=node.start_point[0] + 1, file_path=file_path,
                    ))

        elif t == "new_expression" and caller:
            callee = self._field_text(node, "constructor", source)
            if callee:
                calls.append(ParsedCall(
                    caller=caller, callee=f"new {callee}",
                    line_number=node.start_point[0] + 1, file_path=file_path,
                ))

        for child in node.children:
            self._walk(child, source, file_path, symbols, imports, calls, parent, in_class, caller)

    def _process_definition(
        self,
        node: Any,
        source: str,
        file_path: str,
        symbols: list[ParsedSymbol],
        imports: list[ParsedImport],
        calls: list[ParsedCall],
        parent: str | None,
        in_class: bool,
        caller: str | None,
    ) -> None:
        t = node.type

        if t in ("class_declaration", "abstract_class_declaration"):
            symbol_type = "class"
        elif t == "interface_declaration":
            symbol_type = "interface"
        elif t == "enum_declaration":
            symbol_type = "enum"
        elif t == "type_alias_declaration":
            symbol_type = "type_alias"
        elif t == "function_declaration":
            symbol_type = "function"
        elif t == "method_definition":
            symbol_type = "method"
        else:
            symbol_type = "class"

        decorators = self._get_decorators(node, source)
        modifiers = self._get_modifiers(node)
        visibility = self._get_visibility(node, source)

        name_node = self._child_by_field(node, "name")
        name = self._text(name_node, source) if name_node else None
        if name is None:
            return

        annotations: list[str] = []
        heritage = next((c for c in node.children if c.type == "class_heritage"), None)
        if heritage:
            for child in heritage.children:
                if child.type in ("extends_clause", "implements_clause"):
                    annotations.append(self._text(child, source))
            if not annotations:
                annotations.append(self._text(heritage, source))

        signature: str | None = None
        parameters: list[dict[str, str]] = []
        return_type: str | None = None
        new_caller: str | None = None

        if symbol_type in ("function", "method"):
            params_node = self._child_by_field(node, "parameters")
            parameters = self._extract_params(params_node, source) if params_node else []
            ret_node = self._child_by_field(node, "return_type")
            return_type = self._clean_type(self._text(ret_node, source)) if ret_node else None
            sig_params = self._text(params_node, source) if params_node else "()"
            signature = f"{name}{sig_params}"
            if return_type:
                signature += f": {return_type}"
            new_caller = name

        body = self._child_by_field(node, "body")
        symbols.append(ParsedSymbol(
            name=name,
            type=symbol_type,
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            signature=signature,
            parent=parent,
            decorators=decorators,
            annotations=annotations,
            parameters=parameters,
            return_type=return_type,
            visibility=visibility,
            metadata={"modifiers": modifiers} if modifiers else {},
        ))

        if body:
            new_in_class = symbol_type == "class"
            self._walk(body, source, file_path, symbols, imports, calls, name, new_in_class, new_caller)

    def _extract_field(
        self, node: Any, source: str, file_path: str, parent: str | None,
    ) -> ParsedSymbol | None:
        name_node = self._child_by_field(node, "property") or self._child_by_field(node, "name")
        if not name_node:
            return None
        modifiers = self._get_modifiers(node)
        return ParsedSymbol(
            name=self._text(name_node, source),
            type="variable",
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            parent=parent,
            decorators=self._get_decorators(node, source),
            visibility=self._get_visibility(node, source),
            metadata={"modifiers": modifiers} if modifiers else {},
        )

    def _get_decorators(self, node: Any, source: str) -> list[str]:
        decorators: list[str] = []
        for child in node.children:
            if child.type == "decorator":
                decorators.append(self._text(child, source).removeprefix("@").strip())
        return decorators

    def _get_modifiers(self, node: Any) -> list[str]:
        return [child.type for child in node.children if child.type in _MODIFIER_TOKENS]

    def _get_visibility(self, node: Any, source: str) -> str:
        for child in node.children:
            if child.type == "accessibility_modifier":
                return self._text(child, source).strip()
        return "public"

    def _extract_imports(self, node: Any, source: str) -> list[ParsedImport]:
        source_node = self._child_by_field(node, "source")
        module = self._text(source_node, source).strip().strip("'\"") if source_node else ""
        is_relative = module.startswith(".")
        line_number = node.start_point[0] + 1

        names: list[tuple[str, str | None]] = []
        clause = next((c for c in node.children if c.type == "import_clause"), None)
        if clause:
            for child in clause.children:
                if child.type == "named_imports":
                    for spec in child.children:
                        if spec.type == "import_specifier":
                            imported = (
                                self._field_text(spec, "name", source)
                                or self._field_text(spec, "imported", source)
                            )
                            names.append((imported, self._field_text(spec, "alias", source)))
                elif child.type == "import_specifier":
                    imported = (
                        self._field_text(child, "name", source)
                        or self._field_text(child, "imported", source)
                    )
                    names.append((imported, self._field_text(child, "alias", source)))
                elif child.type == "namespace_import":
                    names.append(("*", None))
                elif child.type == "identifier":
                    names.append((self._text(child, source), None))

        if not names:
            return [ParsedImport(
                module=module, is_relative=is_relative, line_number=line_number,
            )]

        return [
            ParsedImport(
                module=module, name=n, alias=a,
                is_relative=is_relative, line_number=line_number,
            )
            for n, a in names
        ]

    def _extract_params(self, params_node: Any, source: str) -> list[dict[str, str]]:
        params: list[dict[str, str]] = []
        for child in params_node.children:
            if child.type in ("required_parameter", "optional_parameter", "rest_parameter"):
                pname = self._field_text(child, "pattern", source) or self._first_identifier(child, source)
                if not pname:
                    continue
                type_node = self._child_by_field(child, "type")
                params.append({
                    "name": pname,
                    "type": self._clean_type(self._text(type_node, source)) if type_node else "",
                })
        return params

    @staticmethod
    def _clean_type(text: str) -> str:
        text = text.strip()
        return text[1:].strip() if text.startswith(":") else text

    def _first_identifier(self, node: Any, source: str) -> str:
        for child in node.children:
            if child.type == "identifier":
                return self._text(child, source)
        return ""

    def _child_by_field(self, node: Any, field_name: str) -> Any | None:
        return node.child_by_field_name(field_name)

    def _field_text(self, node: Any, field_name: str, source: str) -> str:
        child = node.child_by_field_name(field_name)
        return self._text(child, source) if child else ""

    def _text(self, node: Any, source: str) -> str:
        return source[node.start_byte:node.end_byte]
