from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
import zipfile

HEADER_ALIASES = {
    "date": "date",
    "ticker": "ticker",
    "symbol": "ticker",
    "side": "side",
    "quantity": "quantity",
    "qty": "quantity",
    "price": "price",
    "fee": "fee",
    "account": "account",
    "memo": "memo",
}

REQUIRED_COLUMNS = {"date", "ticker", "side", "quantity", "price"}
NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _normalize_header(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    return HEADER_ALIASES.get(text, text)


def _col_index(cell_ref: str) -> int:
    letters = ""
    for ch in cell_ref:
        if ch.isalpha():
            letters += ch
        else:
            break

    result = 0
    for ch in letters:
        result = result * 26 + (ord(ch.upper()) - ord("A") + 1)

    return result - 1


def _read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    shared_path = "xl/sharedStrings.xml"
    if shared_path not in zf.namelist():
        return []

    root = ET.fromstring(zf.read(shared_path))
    values: list[str] = []

    for si in root.findall("x:si", NS):
        text_parts = [node.text or "" for node in si.findall(".//x:t", NS)]
        values.append("".join(text_parts))

    return values


def _read_sheet_rows(path: Path) -> list[list[Any]]:
    with zipfile.ZipFile(path) as zf:
        shared_strings = _read_shared_strings(zf)
        sheet_xml = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))

    rows: list[list[Any]] = []
    for row in sheet_xml.findall(".//x:sheetData/x:row", NS):
        parsed_row: list[Any] = []

        for cell in row.findall("x:c", NS):
            ref = cell.get("r", "A1")
            idx = _col_index(ref)

            while len(parsed_row) <= idx:
                parsed_row.append(None)

            cell_type = cell.get("t")
            value_node = cell.find("x:v", NS)

            if value_node is None:
                parsed_row[idx] = None
                continue

            raw = value_node.text
            if cell_type == "s" and raw is not None:
                parsed_row[idx] = shared_strings[int(raw)]
            else:
                parsed_row[idx] = raw

        rows.append(parsed_row)

    return rows


def parse_shinhan_xlsx(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        rows = _read_sheet_rows(path)
    except Exception as exc:  # noqa: BLE001
        return [], [{"row": 0, "error": f"invalid xlsx: {exc}"}]

    if not rows:
        return [], [{"row": 0, "error": "empty file"}]

    headers = [_normalize_header(col) for col in rows[0]]
    header_index = {name: idx for idx, name in enumerate(headers) if name}

    missing = REQUIRED_COLUMNS - set(header_index.keys())
    if missing:
        return [], [{"row": 1, "error": f"missing required columns: {', '.join(sorted(missing))}"}]

    parsed: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for row_number, row in enumerate(rows[1:], start=2):
        if all(cell in (None, "") for cell in row):
            continue

        try:
            trade = {
                "date": str(row[header_index["date"]]).strip(),
                "ticker": str(row[header_index["ticker"]]).strip(),
                "side": str(row[header_index["side"]]).strip().lower(),
                "quantity": float(row[header_index["quantity"]]),
                "price": float(row[header_index["price"]]),
                "fee": (
                    float(row[header_index["fee"]])
                    if "fee" in header_index and row[header_index["fee"]] not in (None, "")
                    else 0.0
                ),
                "account": (
                    str(row[header_index["account"]]).strip()
                    if "account" in header_index and row[header_index["account"]] not in (None, "")
                    else None
                ),
                "memo": (
                    str(row[header_index["memo"]]).strip()
                    if "memo" in header_index and row[header_index["memo"]] not in (None, "")
                    else None
                ),
            }

            if trade["side"] not in {"buy", "sell"}:
                raise ValueError("side must be buy or sell")
            if trade["quantity"] <= 0 or trade["price"] <= 0:
                raise ValueError("quantity and price must be positive")

            parsed.append(trade)
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": row_number, "error": str(exc)})

    return parsed, errors
