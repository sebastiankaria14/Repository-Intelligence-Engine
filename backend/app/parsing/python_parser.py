"""
Repository Intelligence Engine — Tree-sitter Python Parser
Extracts classes, functions/methods, imports, decorators, parameters and call
relationships from Python source files using the tree-sitter Python grammar.
"""

from __future__ import annotations

from typing import Any

import tree_sitter_python as tspy
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

PY_LANGUAGE = Language(tspy.language())

_FUNCTION_TYPES = ("function_definition", "async_function_definition")
_DEFINITION_TYPES = ("function_definition", "async_function_definition", "class_definition")


class TreeSitterPythonParser(Parser):
    """Parser for Python source files using tree-sitter."""

    def __init__(self):
        self._parser = TSParser(PY_LANGUAGE)

    @property
    def supported_extensions(self) -> list[str]:
        return [".py"]

    @property
    def language_name(self) -> str:
        return "Python"

    def parse(self, file_path: str, source_code: str) -> ParseResult:
        tree = self._parser.parse(source_code.encode("utf-8"))
        root = tree.root_node

        symbols: list[ParsedSymbol] = []
        imports: list[ParsedImport] = []
        calls: list[ParsedCall] = []

        self._walk(
            root,
            source_code,
            file_path,
            symbols,
            imports,
            calls,
            parent=None,
            in_class=False,
            caller=None,
        )

        lines_of_code = len([line for line in source_code.splitlines() if line.strip()])

        return ParseResult(
            file_path=file_path,
            language="Python",
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
            imp = self._extract_import(node, source)
            if imp:
                imports.append(imp)

        elif t == "import_from_statement":
            imports.extend(self._extract_from_imports(node, source))

        elif t == "decorated_definition":
            decorators = [
                self._decorator_text(d, source)
                for d in node.children
                if d.type == "decorator"
            ]
            for child in node.children:
                if child.type in _DEFINITION_TYPES:
                    self._process_definition(
                        child, decorators, source, file_path,
                        symbols, imports, calls, parent, in_class, caller,
                    )
                    return

        elif t in _DEFINITION_TYPES:
            self._process_definition(
                node, [], source, file_path,
                symbols, imports, calls, parent, in_class, caller,
            )
            return

        elif t == "call":
            if caller:
                callee = self._field_text(node, "function", source)
                if callee:
                    calls.append(ParsedCall(
                        caller=caller,
                        callee=callee,
                        line_number=node.start_point[0] + 1,
                        file_path=file_path,
                    ))

        for child in node.children:
            self._walk(
                child, source, file_path, symbols, imports, calls,
                parent, in_class, caller,
            )

    def _process_definition(
        self,
        node: Any,
        decorators: list[str],
        source: str,
        file_path: str,
        symbols: list[ParsedSymbol],
        imports: list[ParsedImport],
        calls: list[ParsedCall],
        parent: str | None,
        in_class: bool,
        caller: str | None,
    ) -> None:
        if node.type == "class_definition":
            sym = self._extract_class(node, source, file_path, parent, decorators)
            if sym:
                symbols.append(sym)
                body = self._child_by_field(node, "body")
                if body:
                    self._walk(body, source, file_path, symbols, imports, calls, sym.name, True, None)

        elif node.type in _FUNCTION_TYPES:
            is_method = in_class
            sym = self._extract_function(node, source, file_path, parent, decorators, is_method)
            if sym:
                symbols.append(sym)
                body = self._child_by_field(node, "body")
                if body:
                    self._walk(body, source, file_path, symbols, imports, calls, sym.name, False, sym.name)

    def _extract_class(
        self, node: Any, source: str, file_path: str, parent: str | None, decorators: list[str],
    ) -> ParsedSymbol | None:
        name_node = self._child_by_field(node, "name")
        if not name_node:
            return None
        name = self._text(name_node, source)

        bases_node = self._child_by_field(node, "superclasses")
        if bases_node:
            bases = self._text(bases_node, source).strip().strip("()")
            annotations = [f"extends {bases}"] if bases else []
        else:
            annotations = []

        return ParsedSymbol(
            name=name,
            type="class",
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            parent=parent,
            decorators=decorators,
            annotations=annotations,
            visibility="public",
        )

    def _extract_function(
        self,
        node: Any,
        source: str,
        file_path: str,
        parent: str | None,
        decorators: list[str],
        is_method: bool,
    ) -> ParsedSymbol | None:
        name_node = self._child_by_field(node, "name")
        if not name_node:
            return None
        name = self._text(name_node, source)

        params_node = self._child_by_field(node, "parameters")
        parameters = self._extract_params(params_node, source) if params_node else []
        return_type_node = self._child_by_field(node, "return_type")
        return_type = self._text(return_type_node, source) if return_type_node else None

        sig_params = self._text(params_node, source) if params_node else "()"
        signature = f"{name}{sig_params}"
        if return_type:
            signature += f" -> {return_type}"

        visibility = "private" if name.startswith("_") else "public"

        return ParsedSymbol(
            name=name,
            type="method" if is_method else "function",
            file_path=file_path,
            line_start=node.start_point[0] + 1,
            line_end=node.end_point[0] + 1,
            signature=signature,
            parent=parent,
            decorators=decorators,
            parameters=parameters,
            return_type=return_type,
            visibility=visibility,
        )

    def _extract_import(self, node: Any, source: str) -> ParsedImport | None:
        module_node = self._child_by_field(node, "name")
        module = self._text(module_node, source) if module_node else ""
        alias_node = self._child_by_field(node, "alias")
        alias = self._text(alias_node, source) if alias_node else None
        return ParsedImport(
            module=module,
            name=None,
            alias=alias,
            line_number=node.start_point[0] + 1,
            is_relative=False,
        )

    def _extract_from_imports(self, node: Any, source: str) -> list[ParsedImport]:
        text = self._text(node, source)
        is_relative = text.lstrip().startswith("from .")
        module_node = self._child_by_field(node, "module_name")
        module = self._text(module_node, source) if module_node else ""
        line_number = node.start_point[0] + 1

        results: list[ParsedImport] = []
        for i in range(node.child_count):
            child = node.child(i)
            if node.field_name_for_child(i) != "name":
                continue
            if child.type == "dotted_name":
                results.append(ParsedImport(
                    module=module, name=self._text(child, source),
                    line_number=line_number, is_relative=is_relative,
                ))
            elif child.type == "aliased_import":
                name_node = self._child_by_field(child, "name")
                alias_node = self._child_by_field(child, "alias")
                imported = self._text(name_node, source) if name_node else ""
                alias = self._text(alias_node, source) if alias_node else None
                results.append(ParsedImport(
                    module=module, name=imported, alias=alias,
                    line_number=line_number, is_relative=is_relative,
                ))
        return results

    def _extract_params(self, params_node: Any, source: str) -> list[dict[str, str]]:
        params: list[dict[str, str]] = []
        for child in params_node.children:
            if child.type in ("typed_parameter", "identifier"):
                param_name = self._first_identifier_text(child, source)
                if not param_name:
                    continue
                type_node = self._child_by_field(child, "type")
                params.append({
                    "name": param_name,
                    "type": self._text(type_node, source) if type_node else "",
                })
        return params

    def _first_identifier_text(self, node: Any, source: str) -> str:
        for child in node.children:
            if child.type == "identifier":
                return self._text(child, source)
        return ""

    def _decorator_text(self, decorator: Any, source: str) -> str:
        return self._text(decorator, source).removeprefix("@").strip()

    def _child_by_field(self, node: Any, field_name: str) -> Any | None:
        return node.child_by_field_name(field_name)

    def _field_text(self, node: Any, field_name: str, source: str) -> str:
        child = node.child_by_field_name(field_name)
        return self._text(child, source) if child else ""

    def _text(self, node: Any, source: str) -> str:
        return source[node.start_byte:node.end_byte]
