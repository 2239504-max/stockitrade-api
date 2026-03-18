from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
import zipfile

from app.services.shinhan_event_mapper import map_shinhan_row_to_event
from app.schemas.events import NormalizedEvent

HEADER_ALIASES = {
    "거래일자": "date",
    "거래명": "trade_name",
    "거래수량": "quantity",
    "거래금액": "amount",
    "제세금/대출이자": "tax",
    "통화코드": "currency",
    "외화정산금액": "fx_settlement_amount",
    "거래번호": "trade_no",
    "종목명": "ticker_name",
    "거래단가": "price",
    "정산금액": "settlement_amount",
    "수수료/fee": "fee",
    "현금잔액": "cash_balance",
    "잔고수량/펀드평가금액": "balance_quantity",
    "상대계좌명": "counterparty_name",
    "상대계좌번호": "counterparty_account",
    "외화거래금액": "fx_trade_amount",
    "외화예수금액": "fx_cash_balance",
    "처리점": "branch",
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


def parse_shinhan_xlsx(
    path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    try:
        rows = _read_sheet_rows(path)
    except Exception as exc:  # noqa: BLE001
        return [], [{"row": 0, "error": f"invalid xlsx: {exc}"}], {}

    if not rows:
        return [], [{"row": 0, "error": "empty file"}], {}

    headers = [_normalize_header(col) for col in rows[0]]
    header_index = {name: idx for idx, name in enumerate(headers) if name}

    missing = REQUIRED_COLUMNS - set(header_index.keys())
    if missing:
        return [], [{"row": 1, "error": f"missing required columns: {', '.join(sorted(missing))}"}], {}

    parsed: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    unknown_trade_names: dict[str, int] = {}

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
    trade_name = (event.raw_trade_name or "").strip() or "(blank)"
    unknown_trade_names[trade_name] = unknown_trade_names.get(trade_name, 0) + 1

    errors.append({
        "row": row_number,
        "error": f"unknown trade_name: {trade_name}",
    })
        except Exception as exc:  # noqa: BLE001
            errors.append({
    "row": row_number,
    "error": f"unknown trade_name: {event.raw_trade_name}",
})
                    
    return parsed, errors, unknown_trade_names
    
