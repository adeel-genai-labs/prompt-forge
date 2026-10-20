"""Tests for src/schema_input.py: parsing pasted DESCRIBE / CREATE TABLE text."""

import pytest

from src.schema_input import format_schemas, parse_schemas

DESCRIBE_TABS = """Table: main.sales.orders
col_name\tdata_type\tcomment
order_id\tbigint\tPrimary key
customer_id\tstring\tnull
order_ts\ttimestamp\tUTC
amount\tdecimal(18,2)\t
order_date\tdate\t
# Partition Information
# col_name\tdata_type\tcomment
order_date\tdate\t
"""

ORDERS_COLUMNS = [
    ("order_id", "bigint"),
    ("customer_id", "string"),
    ("order_ts", "timestamp"),
    ("amount", "decimal(18,2)"),
    ("order_date", "date"),
]


def test_parses_tab_separated_describe_and_stops_at_partition_section():
    assert parse_schemas(DESCRIBE_TABS) == {"main.sales.orders": ORDERS_COLUMNS}


def test_stops_at_detailed_table_information_section():
    text = "Table: main.a.b\nid  bigint\n# Detailed Table Information\nOwner  someone\nType  MANAGED"
    assert parse_schemas(text) == {"main.a.b": [("id", "bigint")]}


def test_parses_space_separated_describe_with_multi_word_comments():
    text = "Table: main.sales.refunds\nrefund_id   bigint   null\nrefund_amount  decimal(18,2)  refund in USD"
    assert parse_schemas(text) == {"main.sales.refunds": [("refund_id", "bigint"), ("refund_amount", "decimal(18,2)")]}


def test_parses_pipe_table_describe_output():
    text = "Table: main.ref.customer_region\n| col_name | data_type | comment |\n|---|---|---|\n| region | string | |"
    assert parse_schemas(text) == {"main.ref.customer_region": [("region", "string")]}


def test_parses_create_table_with_nested_types_and_constraints():
    text = """CREATE TABLE IF NOT EXISTS `main`.`sales`.`orders` (
      order_id BIGINT NOT NULL COMMENT 'pk, unique',
      amount DECIMAL(18,2),
      tags ARRAY<STRING>,
      info STRUCT<a: INT, b: STRING>,
      CONSTRAINT pk PRIMARY KEY (order_id)
    ) USING DELTA PARTITIONED BY (order_date);"""
    assert parse_schemas(text) == {
        "main.sales.orders": [
            ("order_id", "BIGINT"),
            ("amount", "DECIMAL(18,2)"),
            ("tags", "ARRAY<STRING>"),
            ("info", "STRUCT<a: INT, b: STRING>"),
        ]
    }


def test_table_header_name_wins_over_short_create_table_name():
    text = "Table: main.sales.orders\nCREATE OR REPLACE TABLE orders (order_id BIGINT, amount DOUBLE)"
    assert parse_schemas(text) == {"main.sales.orders": [("order_id", "BIGINT"), ("amount", "DOUBLE")]}


def test_parses_multiple_tables_in_order():
    text = DESCRIBE_TABS + "\nTable: main.sales.refunds\nrefund_id  bigint\norder_id  bigint\n" + (
        "CREATE TABLE main.ref.fx_rates (rate_date DATE, currency STRING, usd_rate DOUBLE)"
    )
    schemas = parse_schemas(text)
    assert list(schemas) == ["main.sales.orders", "main.sales.refunds", "main.ref.fx_rates"]
    assert schemas["main.sales.refunds"] == [("refund_id", "bigint"), ("order_id", "bigint")]
    assert schemas["main.ref.fx_rates"] == [("rate_date", "DATE"), ("currency", "STRING"), ("usd_rate", "DOUBLE")]


def test_create_table_without_header_is_named_by_statement():
    text = "Some notes first.\nCREATE TABLE main.ref.fx_rates (rate_date DATE, usd_rate DOUBLE);"
    assert parse_schemas(text) == {"main.ref.fx_rates": [("rate_date", "DATE"), ("usd_rate", "DOUBLE")]}


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   \n\n",
        "hello world this is not a schema",
        "Table: x.y.z\nfoo bar baz\nmore words here",  # header but no real types
        "order_id bigint\namount double",  # columns but no table name
        "CREATE TABLE broken (",  # unterminated
        "Table:\n\t\t\n|||",
    ],
)
def test_garbage_input_returns_empty_dict(text):
    assert parse_schemas(text) == {}


def test_never_raises_on_odd_input():
    assert parse_schemas("Table: a.b.c\n" + "\x00\t(<,>)'\"" * 50) == {}


def test_format_schemas_is_one_compact_line_per_table():
    schemas = {"main.sales.orders": [("order_id", "bigint"), ("amount", "decimal(18,2)")], "main.a.b": [("id", "int")]}
    assert format_schemas(schemas) == "main.sales.orders: order_id bigint, amount decimal(18,2)\nmain.a.b: id int"


def test_format_schemas_of_nothing_is_empty():
    assert format_schemas({}) == ""
