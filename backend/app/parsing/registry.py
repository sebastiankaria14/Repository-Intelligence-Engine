"""
Repository Intelligence Engine — Parser Registry
Maps file extensions to the appropriate parser implementation.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.parsing.base import Parser, ParseResult

log = get_logger(__name__)


class ParserRegistry:
    """
    Registry that maps file extensions to parser implementations.
    Parsers are registered in priority order — the first matching parser wins.
    """

    def __init__(self):
        self._parsers: list[Parser] = []
        self._extension_map: dict[str, Parser] = {}

    def register(self, parser: Parser) -> None:
        """Register a parser for its supported extensions."""
        self._parsers.append(parser)
        for ext in parser.supported_extensions:
            if ext not in self._extension_map:
                self._extension_map[ext] = parser
                log.debug("parser_registered", extension=ext, parser=parser.language_name)

    def get_parser(self, file_path: str) -> Parser | None:
        """Get the appropriate parser for a file."""
        for ext, parser in self._extension_map.items():
            if file_path.endswith(ext):
                return parser
        return None

    def parse_file(self, file_path: str, source_code: str) -> ParseResult | None:
        """Parse a file using the appropriate parser."""
        parser = self.get_parser(file_path)
        if not parser:
            return None
        try:
            return parser.parse(file_path, source_code)
        except Exception as e:  # noqa: BLE001 - any parse failure is recorded, not propagated
            log.error("parse_error", file=file_path, parser=parser.language_name, error=str(e))
            return ParseResult(
                file_path=file_path,
                language=parser.language_name,
                errors=[str(e)],
            )

    @property
    def supported_extensions(self) -> list[str]:
        return list(self._extension_map.keys())


def create_default_registry() -> ParserRegistry:
    """
    Create the default parser registry with all available parsers.
    Priority: Python > TypeScript/JavaScript > Java
    """
    registry = ParserRegistry()

    # Register Python parser
    try:
        from app.parsing.python_parser import TreeSitterPythonParser
        registry.register(TreeSitterPythonParser())
        log.info("parser_loaded", parser="TreeSitterPythonParser")
    except (ImportError, AttributeError) as e:
        log.warning("parser_load_failed", parser="Python", error=str(e))

    # Register TypeScript/JavaScript parser
    try:
        from app.parsing.typescript_parser import TreeSitterTSJSParser
        registry.register(TreeSitterTSJSParser())
        log.info("parser_loaded", parser="TreeSitterTSJSParser")
    except (ImportError, AttributeError) as e:
        log.warning("parser_load_failed", parser="TypeScript/JavaScript", error=str(e))

    # Register Java parser
    try:
        from app.parsing.java_parser import TreeSitterJavaParser
        registry.register(TreeSitterJavaParser())
        log.info("parser_loaded", parser="TreeSitterJavaParser")
    except (ImportError, AttributeError) as e:
        log.warning("parser_load_failed", parser="Java", error=str(e))

    # Register Go parser
    try:
        from app.parsing.go_parser import TreeSitterGoParser
        registry.register(TreeSitterGoParser())
        log.info("parser_loaded", parser="TreeSitterGoParser")
    except (ImportError, AttributeError) as e:
        log.warning("parser_load_failed", parser="Go", error=str(e))

    # Register Rust parser
    try:
        from app.parsing.rust_parser import TreeSitterRustParser
        registry.register(TreeSitterRustParser())
        log.info("parser_loaded", parser="TreeSitterRustParser")
    except (ImportError, AttributeError) as e:
        log.warning("parser_load_failed", parser="Rust", error=str(e))

    return registry


# Global registry instance
parser_registry = create_default_registry()
