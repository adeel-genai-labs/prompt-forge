"""Parse table schemas the user pastes: Databricks DESCRIBE TABLE output or CREATE TABLE statements.

Best effort: pasted text can be anything, so parsing never raises and returns {} when nothing is found.
Expected format: a line "Table: catalog.schema.table" followed by that table's DESCRIBE output or
CREATE TABLE statement. A CREATE TABLE statement also works on its own, named by the statement.
"""

import re

TABLE_HEADER = re.compile(r"^\s*Table\s*:\s*(\S+)\s*$", re.IGNORECASE)
CREATE_TABLE = re.compile(
    r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:EXTERNAL\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`\w.]+)\s*\(", re.IGNORECASE
)
COLUMN_NAME = re.compile(r"^`?[A-Za-z_]\w*`?$")
# Spark / Databricks type names; anything else on a line is treated as noise, not a column.
DATA_TYPE = re.compile(
    r"^(string|bigint|int|integer|smallint|tinyint|long|short|byte|double|float|real|decimal|numeric|dec|"
    r"boolean|bool|date|timestamp|timestamp_ntz|timestamp_ltz|binary|array|map|struct|variant|interval|"
    r"char|varchar|void|object)\b",
    re.IGNORECASE,
)
# Column options that end the type in a CREATE TABLE column definition.
COLUMN_OPTIONS = re.compile(r"\s+(?:NOT\s+NULL|NULL|COMMENT|GENERATED|DEFAULT|MASK|CONSTRAINT)\b.*$", re.IGNORECASE | re.DOTALL)
CONSTRAINT_LINE = re.compile(r"^(?:CONSTRAINT|PRIMARY\s+KEY|FOREIGN\s+KEY)\b", re.IGNORECASE)


def parse_schemas(text: str) -> dict[str, list[tuple[str, str]]]:
    """Return table name -> [(column, type)] parsed from pasted schema text, or {} if nothing parsed."""
    schemas: dict[str, list[tuple[str, str]]] = {}
    try:
        for header_name, body in split_table_blocks(text):
            create_tables, rest = parse_create_tables(body)
            describe_columns = parse_describe(rest) if header_name else []
            if describe_columns:
                schemas[header_name] = describe_columns
            for create_name, columns in create_tables:
                # The "Table:" line holds the full name the user wants (CREATE may use a short one),
                # but only when that CREATE statement is the block's only table.
                name = header_name if header_name and not describe_columns and len(create_tables) == 1 else create_name
                if columns:
                    schemas[name] = columns
    except Exception:  # best effort: never let odd pasted text break the request
        return {}
    return schemas


def split_table_blocks(text: str) -> list[tuple[str | None, str]]:
    """Split text at "Table: name" lines; return (name or None, body) pairs in order."""
    blocks: list[tuple[str | None, list[str]]] = [(None, [])]
    for line in text.splitlines():
        header = TABLE_HEADER.match(line)
        if header:
            blocks.append((clean_name(header.group(1)), []))
        else:
            blocks[-1][1].append(line)
    return [(name, "\n".join(lines)) for name, lines in blocks if name or any(line.strip() for line in lines)]


def parse_describe(body: str) -> list[tuple[str, str]]:
    """Return (column, type) pairs from DESCRIBE TABLE output, stopping at the first "#" section."""
    columns: list[tuple[str, str]] = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            break  # "# Partition Information", "# Detailed Table Information", ... repeat or describe metadata
        if not stripped or set(stripped) <= set("-+| "):
            continue
        parts = split_describe_line(stripped)
        if len(parts) < 2:
            continue
        name, data_type = parts[0].strip(), parts[1].strip()
        if is_column(name, data_type) and name.strip("`") not in {column for column, _ in columns}:
            columns.append((name.strip("`"), data_type))
    return columns


def split_describe_line(line: str) -> list[str]:
    """Split one DESCRIBE row into cells: tab-separated, pipe-table, or space-separated."""
    if "\t" in line:
        return line.split("\t")
    if line.startswith("|"):
        return [cell for cell in line.strip("|").split("|")]
    return line.split(None, 2)


def parse_create_tables(body: str) -> tuple[list[tuple[str, list[tuple[str, str]]]], str]:
    """Return ([(table name, [(column, type)])] for each CREATE TABLE statement, body without those statements)."""
    tables = []
    rest = body
    for match in CREATE_TABLE.finditer(body):
        column_list = text_until_closing_paren(body, match.end())
        rest = rest.replace(body[match.start() : match.end() + len(column_list) + 1], "")
        columns = []
        for definition in split_top_level(column_list):
            definition = definition.strip()
            if not definition or CONSTRAINT_LINE.match(definition):
                continue
            parts = definition.split(None, 1)
            if len(parts) < 2:
                continue
            name, data_type = parts[0], COLUMN_OPTIONS.sub("", parts[1]).strip()
            if is_column(name, data_type):
                columns.append((name.strip("`"), data_type))
        tables.append((clean_name(match.group(1)), columns))
    return tables, rest


def text_until_closing_paren(text: str, start: int) -> str:
    """Return text from start up to the parenthesis that closes the one just before start."""
    depth = 1
    for index in range(start, len(text)):
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
            if depth == 0:
                return text[start:index]
    return text[start:]


def split_top_level(text: str) -> list[str]:
    """Split on commas that aren't inside (), <> or quotes, e.g. DECIMAL(18,2) or STRUCT<a:INT,b:INT>."""
    parts, current, depth, quote = [], [], 0, ""
    for char in text:
        if quote:
            quote = "" if char == quote else quote
        elif char in "'\"":
            quote = char
        elif char in "(<":
            depth += 1
        elif char in ")>":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    parts.append("".join(current))
    return parts


def is_column(name: str, data_type: str) -> bool:
    """Return True if name looks like a column name and data_type starts with a known type."""
    return bool(COLUMN_NAME.match(name)) and bool(DATA_TYPE.match(data_type)) and name.lower() != "col_name"


def clean_name(name: str) -> str:
    """Return a table name without backticks or a trailing semicolon/comma."""
    return name.replace("`", "").rstrip(";,")


def format_schemas(schemas: dict[str, list[tuple[str, str]]]) -> str:
    """Return a compact block for the model: one line per table, columns with their types."""
    lines = []
    for table, columns in schemas.items():
        column_list = ", ".join(f"{name} {data_type}" for name, data_type in columns)
        lines.append(f"{table}: {column_list}")
    return "\n".join(lines)
