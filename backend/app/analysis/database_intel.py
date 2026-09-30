"""
Repository Intelligence Engine — Database Intelligence
Discovers database schemas, ORM models, tables, columns, foreign keys,
and relationships from parsed source code.
"""

from __future__ import annotations

import re
from collections import defaultdict

from app.core.logging import get_logger

log = get_logger(__name__)

# ORM model base classes
ORM_BASES = {
    "Model", "Base", "DeclarativeBase", "db.Model",  # SQLAlchemy/Flask
    "models.Model", "Model",  # Django
    "Entity", "BaseEntity",  # TypeORM / JPA
    "Schema",  # Mongoose
}

# Column type mappings
SQL_TYPES = {
    "String": "VARCHAR", "Integer": "INTEGER", "Float": "FLOAT",
    "Boolean": "BOOLEAN", "Text": "TEXT", "DateTime": "DATETIME",
    "Date": "DATE", "JSON": "JSON", "UUID": "UUID",
    "BigInteger": "BIGINT", "SmallInteger": "SMALLINT",
    "Numeric": "NUMERIC", "LargeBinary": "BLOB",
    "ForeignKey": "FK", "Enum": "ENUM",
    # Django
    "CharField": "VARCHAR", "IntegerField": "INTEGER",
    "BooleanField": "BOOLEAN", "TextField": "TEXT",
    "DateTimeField": "DATETIME", "DateField": "DATE",
    "FloatField": "FLOAT", "ForeignKey": "FK",
    "ManyToManyField": "M2M", "OneToOneField": "1:1",
    "AutoField": "INTEGER", "BigAutoField": "BIGINT",
    "UUIDField": "UUID", "JSONField": "JSON",
    # TypeORM / Java
    "varchar": "VARCHAR", "int": "INTEGER", "boolean": "BOOLEAN",
}


def analyze_database(
    files: list[dict],
    symbols: list[dict],
    imports: list[dict],
) -> dict:
    """Discover database schemas from ORM model definitions."""
    tables: list[dict] = []
    relationships: list[dict] = []

    # Find classes that look like ORM models
    model_classes = _find_orm_models(symbols, imports)

    for model in model_classes:
        table = _extract_table(model, symbols)
        if table:
            tables.append(table)

    # Detect relationships from foreign keys
    for table in tables:
        for fk in table.get("foreign_keys", []):
            relationships.append({
                "from_table": table["name"],
                "to_table": fk["referenced_table"],
                "type": fk.get("rel_type", "many-to-one"),
            })

    # Find SQL migration files
    migrations = _find_migrations(files)

    # Build ER diagram
    er_diagram = _build_er_diagram(tables, relationships)

    return {
        "tables": tables,
        "relationships": relationships,
        "migrations": migrations,
        "er_diagram": er_diagram,
    }


def _find_orm_models(symbols: list[dict], imports: list[dict]) -> list[dict]:
    """Find class symbols that are ORM models."""
    # Check if ORM imports exist
    orm_modules = {"sqlalchemy", "django.db", "typeorm", "mongoose", "sequelize", "prisma", "peewee"}
    has_orm = any(imp.get("module", "").lower().split(".")[0] in orm_modules for imp in imports)

    models = []
    for sym in symbols:
        if sym["type"] != "class":
            continue

        # Check if the class name suggests a model
        name = sym.get("name", "")
        is_model = False

        # Check parent class / annotations
        annotations = sym.get("annotations", [])
        decorators = sym.get("decorators", [])

        # Direct ORM base class
        for ann in annotations:
            if any(base in ann for base in ORM_BASES):
                is_model = True
                break

        # Django or Flask-SQLAlchemy decorators
        for dec in decorators:
            if "Entity" in dec or "Table" in dec or "model" in dec.lower():
                is_model = True
                break

        # Heuristic: class name + file path suggests a model
        file_path = sym.get("file_path", "").lower()
        if "model" in file_path or "schema" in file_path or "entities" in file_path:
            is_model = True

        if is_model or has_orm:
            models.append(sym)

    return models


def _extract_table(model: dict, all_symbols: list[dict]) -> dict | None:
    """Extract table schema from a class definition."""
    table_name = _class_to_table_name(model["name"])
    columns = []
    foreign_keys = []

    # Find child symbols (methods and fields) in the same file
    for sym in all_symbols:
        if sym.get("parent") != model["name"]:
            continue
        if sym.get("file_path") != model["file_path"]:
            continue

        if sym["type"] == "variable":
            col = _parse_column(sym)
            if col:
                if col.get("is_fk"):
                    foreign_keys.append({
                        "column": col["name"],
                        "referenced_table": col.get("fk_table", "unknown"),
                        "referenced_column": "id",
                        "rel_type": col.get("rel_type", "many-to-one"),
                    })
                columns.append(col)

    if not columns:
        # If no explicit columns found, use the class as a placeholder
        columns.append({
            "name": "id",
            "type": "UUID",
            "nullable": False,
            "default_value": None,
        })

    return {
        "name": table_name,
        "columns": columns,
        "foreign_keys": foreign_keys,
        "indexes": [],
        "source_file": model["file_path"],
        "orm_model": model["name"],
    }


def _parse_column(sym: dict) -> dict | None:
    """Parse a class field/variable into a column definition."""
    name = sym.get("name", "")
    if name.startswith("_") and not name.startswith("__tablename"):
        return None

    col: dict = {
        "name": name,
        "type": "VARCHAR",
        "nullable": True,
        "default_value": None,
        "is_fk": False,
    }

    # Detect type from return_type or signature
    sig = sym.get("signature", "") or sym.get("return_type", "") or ""
    for type_name, sql_type in SQL_TYPES.items():
        if type_name in sig:
            col["type"] = sql_type
            break

    # Detect foreign keys
    if "ForeignKey" in sig or "foreign_key" in name.lower() or name.endswith("_id"):
        col["is_fk"] = True
        col["fk_table"] = name.replace("_id", "").replace("Id", "")

    # Detect nullable
    if "nullable=False" in sig or "NOT NULL" in sig:
        col["nullable"] = False

    return col


def _class_to_table_name(class_name: str) -> str:
    """Convert CamelCase class name to snake_case table name."""
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()
    if not s.endswith("s"):
        s += "s"
    return s


def _find_migrations(files: list[dict]) -> list[dict]:
    """Find database migration files."""
    migrations = []
    for f in files:
        path = f["path"].lower()
        if any(p in path for p in ("migration", "alembic/versions", "db/migrate")):
            name = f["path"].split("/")[-1]
            migrations.append({
                "id": name.split("_")[0] if "_" in name else name,
                "name": name,
                "applied_at": "",
            })
    return sorted(migrations, key=lambda m: m["name"])


def _build_er_diagram(tables: list[dict], relationships: list[dict]) -> dict:
    """Build a React Flow ER diagram with rich entityNode data and handles."""
    nodes = []
    edges = []

    for i, table in enumerate(tables):
        col_labels = [f"{c['name']}: {c['type']}" for c in table.get("columns", [])[:8]]
        label = f"{table['name']}\n{'─' * 20}\n" + "\n".join(col_labels)

        nodes.append({
            "id": table["name"],
            "type": "entityNode",
            "position": {"x": (i % 3) * 380 + 40, "y": (i // 3) * 340 + 40},
            "data": {
                "label": table["name"],
                "table": table,
            },
        })

    for i, rel in enumerate(relationships):
        edges.append({
            "id": f"rel-{rel['from_table']}-{rel['to_table']}-{i}",
            "source": rel["from_table"],
            "target": rel["to_table"],
            "label": rel.get("type", "FK"),
            "animated": True,
            "style": {
                "stroke": "#a855f7",
                "strokeWidth": 2,
            },
        })

    return {"nodes": nodes, "edges": edges}
