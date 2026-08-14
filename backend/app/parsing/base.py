"""
Repository Intelligence Engine — Parser Base
Abstract base class for all source code parsers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedSymbol:
    """A single parsed code symbol (class, function, method, etc.)."""
    name: str
    type: str  # class, function, method, interface, variable, import, decorator
    file_path: str
    line_start: int
    line_end: int
    signature: str | None = None
    docstring: str | None = None
    parent: str | None = None  # Parent class/module name
    decorators: list[str] = field(default_factory=list)
    annotations: list[str] = field(default_factory=list)
    parameters: list[dict[str, str]] = field(default_factory=list)
    return_type: str | None = None
    visibility: str = "public"  # public, private, protected
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedImport:
    """A parsed import statement."""
    module: str
    name: str | None = None  # specific import (e.g., from X import Y → Y)
    alias: str | None = None
    is_relative: bool = False
    line_number: int = 0


@dataclass
class ParsedCall:
    """A parsed function/method call."""
    caller: str  # Qualified name of the calling function
    callee: str  # Name of the called function/method
    line_number: int = 0
    file_path: str = ""


@dataclass
class ParseResult:
    """Complete parse result for a single source file."""
    file_path: str
    language: str
    symbols: list[ParsedSymbol] = field(default_factory=list)
    imports: list[ParsedImport] = field(default_factory=list)
    calls: list[ParsedCall] = field(default_factory=list)
    lines_of_code: int = 0
    errors: list[str] = field(default_factory=list)


class Parser(ABC):
    """Abstract base class for language-specific parsers."""

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """File extensions this parser can handle."""
        ...

    @property
    @abstractmethod
    def language_name(self) -> str:
        """Human-readable language name."""
        ...

    @abstractmethod
    def parse(self, file_path: str, source_code: str) -> ParseResult:
        """
        Parse a single source file and extract all symbols, imports, and calls.

        Args:
            file_path: Path to the source file (relative to repo root).
            source_code: The file content as a string.

        Returns:
            ParseResult with all extracted information.
        """
        ...

    def can_parse(self, file_path: str) -> bool:
        """Check if this parser can handle the given file."""
        return any(file_path.endswith(ext) for ext in self.supported_extensions)
