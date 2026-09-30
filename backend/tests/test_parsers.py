"""
RIE Backend — Source Code Parser Tests
Validates the tree-sitter Java, Python and TypeScript/JavaScript parsers and
the parser registry that dispatches between them.
"""

import pytest

pytest.importorskip("tree_sitter")
pytest.importorskip("tree_sitter_python")
pytest.importorskip("tree_sitter_javascript")
pytest.importorskip("tree_sitter_typescript")
pytest.importorskip("tree_sitter_java")
pytest.importorskip("tree_sitter_typescript")
pytest.importorskip("tree_sitter_java")

from app.parsing.java_parser import TreeSitterJavaParser
from app.parsing.python_parser import TreeSitterPythonParser
from app.parsing.registry import parser_registry
from app.parsing.typescript_parser import TreeSitterTSJSParser

_JAVA = """import java.util.List;
import java.util.*;
public class Hello extends Base implements Iface {
    private int count;
    public void greet(String name) {
        System.out.println(name);
        List items = new ArrayList();
    }
}
"""

_PYTHON = """import os
from a.b import c, d as e
@deco
class Sub(Base):
    def meth(self, x: int = 5) -> str:
        return str(x)
"""

_TYPESCRIPT = """import {Foo} from 'mod'
import * as ns from 'n'
import d from 'default'
interface I { x: number }
enum E { A, B }
type T = string
abstract class C<T> extends B implements I {
  private async foo(a: string): number { return bar(a); }
  protected s: number = 1
  static hello() { new Bar(); }
}
"""

_JAVASCRIPT = """import {a} from 'm'
import x from 'j'
class A extends B {
  m() { foo(); obj.bar(); new D(); }
  static s = 2
}
function f(p) { return f2(); }
"""


def _by_name(result, name):
    return next(s for s in result.symbols if s.name == name)


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #


def test_registry_supports_all_languages():
    exts = set(parser_registry.supported_extensions)
    assert {".py", ".ts", ".tsx", ".js", ".jsx", ".java"} <= exts


def test_registry_dispatches_to_correct_parser():
    assert isinstance(parser_registry.get_parser("x.java"), TreeSitterJavaParser)
    assert isinstance(parser_registry.get_parser("x.py"), TreeSitterPythonParser)
    assert isinstance(parser_registry.get_parser("x.ts"), TreeSitterTSJSParser)
    assert isinstance(parser_registry.get_parser("x.js"), TreeSitterTSJSParser)
    assert parser_registry.get_parser("x.unknown") is None


def test_registry_parse_file_routes_correctly():
    result = parser_registry.parse_file("Example.java", _JAVA)
    assert result is not None
    assert result.language == "Java"
    assert _by_name(result, "Hello").type == "class"
    assert parser_registry.parse_file("README.md", "") is None


# --------------------------------------------------------------------------- #
# Java
# --------------------------------------------------------------------------- #


def test_java_parser_extracts_symbols():
    result = TreeSitterJavaParser().parse("Hello.java", _JAVA)

    hello = _by_name(result, "Hello")
    assert hello.type == "class"
    assert hello.parent is None
    assert hello.visibility == "public"
    assert "extends Base" in hello.annotations
    assert "implements Iface" in hello.annotations

    count = _by_name(result, "count")
    assert count.type == "variable"
    assert count.parent == "Hello"
    assert count.visibility == "private"

    greet = _by_name(result, "greet")
    assert greet.type == "method"
    assert greet.parent == "Hello"
    assert greet.visibility == "public"
    assert greet.return_type == "void"
    assert greet.signature == "void greet(String name)"
    assert [{"name": "name", "type": "String"}] == greet.parameters


def test_java_parser_extracts_imports_and_calls():
    result = TreeSitterJavaParser().parse("Hello.java", _JAVA)

    modules = {i.module for i in result.imports}
    assert modules == {"java.util"}
    assert {i.name for i in result.imports if i.module == "java.util"} == {"List", "*"}

    callees = {c.callee for c in result.calls}
    assert "System.out.println" in callees
    assert "new ArrayList" in callees


# --------------------------------------------------------------------------- #
# Python
# --------------------------------------------------------------------------- #


def test_python_parser_extracts_definitions_and_imports():
    result = TreeSitterPythonParser().parse("mod.py", _PYTHON)

    sub = _by_name(result, "Sub")
    assert sub.type == "class"
    assert sub.decorators == ["deco"]
    assert "extends Base" in sub.annotations

    meth = _by_name(result, "meth")
    assert meth.type == "method"
    assert meth.parent == "Sub"
    assert meth.return_type == "str"
    assert meth.signature == "meth(self, x: int = 5) -> str"

    by_module = {(i.module, i.name, i.alias) for i in result.imports}
    assert ("os", None, None) in by_module
    assert ("a.b", "c", None) in by_module
    assert ("a.b", "d", "e") in by_module


def test_python_parser_extracts_calls():
    result = TreeSitterPythonParser().parse("mod.py", _PYTHON)
    assert len(result.calls) == 1
    call = result.calls[0]
    assert call.caller == "meth"
    assert call.callee == "str"


def test_python_parser_counts_loc():
    result = TreeSitterPythonParser().parse("mod.py", _PYTHON)
    assert result.lines_of_code == 6


# --------------------------------------------------------------------------- #
# TypeScript
# --------------------------------------------------------------------------- #


def test_typescript_parser_extracts_types():
    result = TreeSitterTSJSParser().parse("f.ts", _TYPESCRIPT)

    assert _by_name(result, "I").type == "interface"
    assert _by_name(result, "E").type == "enum"
    assert _by_name(result, "T").type == "type_alias"

    cls = _by_name(result, "C")
    assert cls.type == "class"
    assert cls.visibility == "public"
    assert "extends B" in cls.annotations
    assert "implements I" in cls.annotations

    foo = _by_name(result, "foo")
    assert foo.type == "method"
    assert foo.parent == "C"
    assert foo.visibility == "private"
    assert foo.return_type == "number"
    assert foo.signature == "foo(a: string): number"
    assert foo.parameters == [{"name": "a", "type": "string"}]

    hello = _by_name(result, "hello")
    assert hello.type == "method"
    assert hello.parent == "C"
    assert hello.visibility == "public"

    field = _by_name(result, "s")
    assert field.type == "variable"
    assert field.parent == "C"


def test_typescript_parser_extracts_imports_and_calls():
    result = TreeSitterTSJSParser().parse("f.ts", _TYPESCRIPT)

    by_module = {(i.module, i.name, i.alias) for i in result.imports}
    assert ("mod", "Foo", "") in by_module
    assert ("n", "*", None) in by_module
    assert ("default", "d", None) in by_module

    by_caller = {(c.caller, c.callee) for c in result.calls}
    assert ("foo", "bar") in by_caller
    assert ("hello", "new Bar") in by_caller


def test_typescript_parser_is_not_javascript():
    ts = TreeSitterTSJSParser().parse("f.ts", _TYPESCRIPT)
    js = TreeSitterTSJSParser().parse("f.js", _JAVASCRIPT)
    assert ts.language == "TypeScript"
    assert js.language == "JavaScript"


# --------------------------------------------------------------------------- #
# JavaScript
# --------------------------------------------------------------------------- #


def test_javascript_parser_extracts_symbols():
    result = TreeSitterTSJSParser().parse("f.js", _JAVASCRIPT)

    cls = _by_name(result, "A")
    assert cls.type == "class"
    assert "extends B" in cls.annotations

    method = _by_name(result, "m")
    assert method.type == "method"
    assert method.parent == "A"
    assert method.visibility == "public"

    field = _by_name(result, "s")
    assert field.type == "variable"
    assert field.parent == "A"

    func = _by_name(result, "f")
    assert func.type == "function"
    assert func.parent is None
    assert func.signature == "f(p)"


def test_javascript_parser_extracts_imports_and_calls():
    result = TreeSitterTSJSParser().parse("f.js", _JAVASCRIPT)

    by_module = {(i.module, i.name, i.alias) for i in result.imports}
    assert ("m", "a", "") in by_module
    assert ("j", "x", None) in by_module

    by_caller = {(c.caller, c.callee) for c in result.calls}
    assert ("m", "foo") in by_caller
    assert ("m", "obj.bar") in by_caller
    assert ("m", "new D") in by_caller
    assert ("f", "f2") in by_caller


# --------------------------------------------------------------------------- #
# Go
# --------------------------------------------------------------------------- #

_GO = """package main

import (
    "fmt"
    "net/http"
)

type Config struct {
    Port int
}

type Runner interface {
    Run() error
}

func (c *Config) Address() string {
    return fmt.Sprintf(":%d", c.Port)
}

func StartServer(cfg *Config) error {
    fmt.Println(cfg.Address())
    return nil
}
"""


def test_go_parser_extracts_symbols():
    from app.parsing.go_parser import TreeSitterGoParser
    result = TreeSitterGoParser().parse("main.go", _GO)

    assert result.language == "Go"

    cfg = _by_name(result, "Config")
    assert cfg.type == "class"
    assert cfg.visibility == "public"

    runner = _by_name(result, "Runner")
    assert runner.type == "interface"
    assert runner.visibility == "public"

    addr = _by_name(result, "Address")
    assert addr.type == "method"
    assert addr.parent == "Config"
    assert addr.return_type == "string"

    start = _by_name(result, "StartServer")
    assert start.type == "function"
    assert start.visibility == "public"


def test_go_parser_extracts_imports_and_calls():
    from app.parsing.go_parser import TreeSitterGoParser
    result = TreeSitterGoParser().parse("main.go", _GO)

    modules = {i.module for i in result.imports}
    assert "fmt" in modules
    assert "net/http" in modules

    callees = {c.callee for c in result.calls}
    assert "fmt.Sprintf" in callees or "fmt.Println" in callees


# --------------------------------------------------------------------------- #
# Rust
# --------------------------------------------------------------------------- #

_RUST = """use std::collections::HashMap;
use std::sync::Arc;

pub struct Engine {
    workers: usize,
}

pub trait Worker {
    fn process(&self);
}

impl Engine {
    pub fn new(workers: usize) -> Self {
        Engine { workers }
    }
}

pub fn execute() {
    let eng = Engine::new(4);
    println!("started");
}
"""


def test_rust_parser_extracts_symbols():
    from app.parsing.rust_parser import TreeSitterRustParser
    result = TreeSitterRustParser().parse("lib.rs", _RUST)

    assert result.language == "Rust"

    eng = _by_name(result, "Engine")
    assert eng.type == "class"
    assert eng.visibility == "public"

    worker = _by_name(result, "Worker")
    assert worker.type == "interface"
    assert worker.visibility == "public"

    new_fn = _by_name(result, "new")
    assert new_fn.type == "method"
    assert new_fn.parent == "Engine"
    assert new_fn.visibility == "public"

    exec = _by_name(result, "execute")
    assert exec.type == "function"
    assert exec.visibility == "public"


def test_rust_parser_extracts_imports_and_calls():
    from app.parsing.rust_parser import TreeSitterRustParser
    result = TreeSitterRustParser().parse("lib.rs", _RUST)

    modules = {i.module for i in result.imports}
    assert any("HashMap" in m for m in modules)

    callees = {c.callee for c in result.calls}
    assert "Engine::new" in callees or "println!" in callees


def test_registry_supports_go_and_rust():
    exts = set(parser_registry.supported_extensions)
    assert ".go" in exts
    assert ".rs" in exts

    from app.parsing.go_parser import TreeSitterGoParser
    from app.parsing.rust_parser import TreeSitterRustParser

    assert isinstance(parser_registry.get_parser("server.go"), TreeSitterGoParser)
    assert isinstance(parser_registry.get_parser("main.rs"), TreeSitterRustParser)

