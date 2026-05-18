"""
Shared utilities for parsing COBOL fixed-width data files in PySpark.

Handles COBOL zoned-decimal sign overpunch decoding (ASCII representation),
field extraction from fixed-width records, and schema loading from JSON.
"""

import json
import os
from decimal import Decimal

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DecimalType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)

# ---------------------------------------------------------------------------
# COBOL ASCII zoned-decimal overpunch lookup tables
# In COBOL DISPLAY format the sign is encoded in the zone nibble of the
# last byte.  For ASCII data the mapping is:
#   Positive:  { = 0, A = 1, B = 2, C = 3, D = 4,
#                E = 5, F = 6, G = 7, H = 8, I = 9
#   Negative:  } = 0, J = 1, K = 2, L = 3, M = 4,
#                N = 5, O = 6, P = 7, Q = 8, R = 9
# ---------------------------------------------------------------------------
POSITIVE_OVERPUNCH = {
    "{": "0", "A": "1", "B": "2", "C": "3", "D": "4",
    "E": "5", "F": "6", "G": "7", "H": "8", "I": "9",
}
NEGATIVE_OVERPUNCH = {
    "}": "0", "J": "1", "K": "2", "L": "3", "M": "4",
    "N": "5", "O": "6", "P": "7", "Q": "8", "R": "9",
}


def decode_signed_zoned_decimal(raw: str, decimal_places: int) -> Decimal:
    """Decode a COBOL signed zoned-decimal (DISPLAY) value from ASCII text.

    The last character carries the sign overpunch.  The implied decimal
    point is inserted according to *decimal_places* (from the PIC V clause).

    Parameters
    ----------
    raw : str
        The raw fixed-width substring, e.g. ``'00000001940{'``.
    decimal_places : int
        Number of digits after the implied decimal (e.g. 2 for V99).

    Returns
    -------
    Decimal
        The decoded numeric value, e.g. ``Decimal('194.00')``.
    """
    if not raw or raw.isspace():
        return Decimal("0")

    last_char = raw[-1]
    leading = raw[:-1]
    sign = 1

    if last_char in POSITIVE_OVERPUNCH:
        digit = POSITIVE_OVERPUNCH[last_char]
        sign = 1
    elif last_char in NEGATIVE_OVERPUNCH:
        digit = NEGATIVE_OVERPUNCH[last_char]
        sign = -1
    elif last_char.isdigit():
        # No overpunch — treat as unsigned positive
        digit = last_char
        sign = 1
    else:
        # Unexpected character — default to zero
        digit = "0"

    digits = leading + digit
    # Insert implied decimal point
    if decimal_places > 0:
        integer_part = digits[:-decimal_places] or "0"
        fractional_part = digits[-decimal_places:]
        value_str = f"{integer_part}.{fractional_part}"
    else:
        value_str = digits

    return Decimal(value_str) * sign


def load_schema(schema_path: str) -> dict:
    """Load a copybook JSON schema file.

    Parameters
    ----------
    schema_path : str
        Absolute or relative path to the JSON schema file.

    Returns
    -------
    dict
        Parsed schema dictionary containing field definitions.
    """
    with open(schema_path, "r") as fh:
        return json.load(fh)


def build_pyspark_schema(fields: list[dict]) -> StructType:
    """Build a PySpark StructType from copybook JSON field definitions.

    Only non-FILLER fields are included in the output schema.

    Parameters
    ----------
    fields : list[dict]
        Field definitions from the JSON schema.

    Returns
    -------
    StructType
        PySpark schema for the parsed DataFrame.
    """
    type_map = {
        "StringType": StringType(),
        "LongType": LongType(),
        "IntegerType": IntegerType(),
    }

    spark_fields = []
    for field in fields:
        if field["name"] == "FILLER":
            continue
        pyspark_type_str = field["pyspark_type"]
        if pyspark_type_str.startswith("DecimalType"):
            # Parse precision and scale from "DecimalType(p,s)"
            inner = pyspark_type_str.replace("DecimalType(", "").rstrip(")")
            precision, scale = [int(x) for x in inner.split(",")]
            spark_type = DecimalType(precision, scale)
        else:
            spark_type = type_map[pyspark_type_str]
        spark_fields.append(StructField(field["name"], spark_type, nullable=True))

    return StructType(spark_fields)


def parse_fixed_width_file(
    spark,
    data_file: str,
    schema_json: dict,
) -> DataFrame:
    """Read a fixed-width COBOL data file and return a parsed PySpark DataFrame.

    Each line of the file is treated as a single record.  Fields are sliced
    by byte offset and length from the JSON schema, then cast to the
    appropriate PySpark types.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    data_file : str
        Path to the fixed-width text file.
    schema_json : dict
        Parsed JSON schema (from ``load_schema``).

    Returns
    -------
    DataFrame
        Parsed DataFrame with one column per non-FILLER field.
    """
    # Read raw lines (each line = one record)
    raw_df = spark.read.text(data_file)

    result_df = raw_df
    select_cols = []

    for field in schema_json["fields"]:
        if field["name"] == "FILLER":
            continue

        # PySpark substring is 1-indexed
        start_pos = field["byte_offset"] + 1
        length = field["length"]
        col_name = field["name"]
        pyspark_type_str = field["pyspark_type"]

        # Extract the raw substring
        raw_col = F.substring(F.col("value"), start_pos, length)

        if pyspark_type_str.startswith("DecimalType"):
            # Signed zoned decimal — decode via UDF (registered per-script)
            # We store the raw substring for now; UDF applied later
            result_df = result_df.withColumn(col_name, raw_col)
        elif pyspark_type_str == "LongType":
            # Unsigned numeric display — cast to long
            result_df = result_df.withColumn(col_name, raw_col.cast("long"))
        elif pyspark_type_str == "IntegerType":
            # Unsigned numeric display — cast to int
            result_df = result_df.withColumn(col_name, raw_col.cast("int"))
        else:
            # Alphanumeric — trim trailing spaces
            result_df = result_df.withColumn(col_name, F.trim(raw_col))

        select_cols.append(col_name)

    return result_df.select(select_cols)


def get_project_root() -> str:
    """Return the absolute path to the project root directory.

    Walks up from this file's location until it finds the repo root
    (identified by the ``app/`` directory).
    """
    current = os.path.dirname(os.path.abspath(__file__))
    while current != "/":
        if os.path.isdir(os.path.join(current, "app")):
            return current
        current = os.path.dirname(current)
    return os.path.dirname(os.path.abspath(__file__))
