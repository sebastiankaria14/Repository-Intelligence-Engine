"""
Repository Intelligence Engine — API Discovery
Discovers REST, GraphQL, WebSocket, and gRPC endpoints from parsed symbols.
"""

from __future__ import annotations

import re

from app.core.logging import get_logger

log = get_logger(__name__)

# Decorator/annotation → HTTP method mapping
ROUTE_DECORATORS = {
    "app.get": "GET", "app.post": "POST", "app.put": "PUT",
    "app.delete": "DELETE", "app.patch": "PATCH",
    "router.get": "GET", "router.post": "POST", "router.put": "PUT",
    "router.delete": "DELETE", "router.patch": "PATCH",
    "api_view": None,
    "GetMapping": "GET", "PostMapping": "POST", "PutMapping": "PUT",
    "DeleteMapping": "DELETE", "PatchMapping": "PATCH", "RequestMapping": None,
    "Get": "GET", "Post": "POST", "Put": "PUT", "Delete": "DELETE", "Patch": "PATCH",
}

FRAMEWORK_PATTERNS = {
    "fastapi": ["FastAPI", "APIRouter", "app.get", "app.post", "router.get"],
    "flask": ["Flask", "Blueprint", "route"],
    "django": ["urlpatterns", "path(", "re_path("],
    "express": ["express", "app.get", "app.post", "router.get", "router.post"],
    "spring": ["@GetMapping", "@PostMapping", "@RestController", "@RequestMapping"],
    "nestjs": ["@Get", "@Post", "@Controller"],
}


def discover_apis(
    files: list[dict],
    symbols: list[dict],
    imports: list[dict],
) -> dict:
    """Discover API endpoints from parsed symbols and decorators."""
    endpoints: list[dict] = []
    frameworks_detected: set[str] = set()

    for sym in symbols:
        if sym["type"] not in ("function", "method"):
            continue

        decorators = sym.get("decorators", [])
        if not decorators:
            continue

        for dec in decorators:
            method, path = _parse_route_decorator(dec)
            if method is not None:
                # Detect framework
                for fw_name, indicators in FRAMEWORK_PATTERNS.items():
                    if any(ind.lower() in dec.lower() for ind in indicators):
                        frameworks_detected.add(fw_name)

                auth_required = _check_auth(decorators, sym)

                endpoints.append({
                    "method": method,
                    "path": path or f"/{sym['name']}",
                    "handler": sym["name"],
                    "file_path": sym["file_path"],
                    "line_number": sym.get("line_start", 0),
                    "parameters": sym.get("parameters", []),
                    "auth_required": auth_required,
                    "middleware": _extract_middleware(decorators),
                    "description": (sym.get("docstring") or "")[:200] or None,
                })

    # Also detect from imports which frameworks are used
    for imp in imports:
        module = imp.get("module", "").lower()
        for fw_name, indicators in FRAMEWORK_PATTERNS.items():
            if any(ind.lower() in module for ind in indicators):
                frameworks_detected.add(fw_name)

    return {
        "endpoints": endpoints,
        "total": len(endpoints),
        "frameworks_detected": sorted(frameworks_detected),
    }


def _parse_route_decorator(decorator: str) -> tuple[str | None, str | None]:
    """Parse a route decorator and extract HTTP method and path."""
    dec_lower = decorator.lower()

    # Check known decorator patterns
    for pattern, method in ROUTE_DECORATORS.items():
        if pattern.lower() in dec_lower:
            # Extract path from parentheses
            path_match = re.search(r'["\']([^"\']+)["\']', decorator)
            path = path_match.group(1) if path_match else None
            return method or "GET", path

    # Flask-style @app.route('/path', methods=['GET', 'POST'])
    if "route" in dec_lower:
        path_match = re.search(r'["\']([^"\']+)["\']', decorator)
        method_match = re.search(r'methods\s*=\s*\[([^\]]+)\]', decorator)
        path = path_match.group(1) if path_match else None
        if method_match:
            methods = method_match.group(1).replace("'", "").replace('"', "").strip()
            return methods.split(",")[0].strip(), path
        return "GET", path

    return None, None


def _check_auth(decorators: list[str], sym: dict) -> bool:
    """Check if the endpoint requires authentication."""
    auth_keywords = [
        "login_required", "auth", "permission", "protect",
        "jwt", "token", "bearer", "api_key", "authenticated",
        "Depends(", "Security(",
    ]
    all_text = " ".join(decorators).lower() + " " + (sym.get("docstring") or "").lower()
    return any(kw.lower() in all_text for kw in auth_keywords)


def _extract_middleware(decorators: list[str]) -> list[str]:
    """Extract middleware from decorators."""
    middleware = []
    middleware_keywords = ["middleware", "before_request", "guard", "interceptor", "pipe"]
    for dec in decorators:
        if any(kw in dec.lower() for kw in middleware_keywords):
            middleware.append(dec)
    return middleware
