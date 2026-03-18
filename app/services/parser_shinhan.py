from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
import zipfile

from app.services.shinhan_event_mapper import map_shinhan_row_to_event
from app.schemas.events import NormalizedEvent

HEADER_ALIASES = {
    "date": "date",
    "일자": "date",

    "ticker": "ticker",
    "symbol": "ticker",
    "종목코드": "ticker",
    "종목명": "ticker_name",

    "side": "side",
    "구분": "side",

    "trade_name": "trade_name",
    "거래명": "trade_name",
    "적요": "trade_name",
    "내용": "trade_name",

    "quantity": "quantity",
    "qty": "quantity",
    "수량": "quantity",

    "price": "price",
    "단가": "price",

    "amount": "amount",
    "금액": "amount",

    "fee": "fee",
    "수수료": "fee",

    "tax": "tax",
    "세금": "tax",

    "currency": "currency",
    "통화": "currency",

    "account": "account",
    "계좌": "account",

    "memo": "memo",
    "메모": "memo",
}

REQUIRED_COLUMNS = {"date", "trade_name"}
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
            normalized_row = {
                key: row[idx] if idx < len(row) else None
                for key, idx in header_index.items()
            }

            event: NormalizedEvent = map_shinhan_row_to_event(
                row_number=row_number,
                row=normalized_row,
            )

            parsed.append(event.model_dump())

            if event.event_type == "UNKNOWN":
                errors.append({
                    "row": row_number,
                    "error": f"unknown trade_name: {event.raw_trade_name}",
                })

        except Exception as exc:  # noqa: BLE001
            errors.append({"row": row_number, "error": str(exc)})
                    
    return parsed, errors
    
