from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
import re
import zipfile

from app.schemas.events import NormalizedEvent
from app.services.shinhan_event_mapper import map_shinhan_row_to_event

NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

# 핵심: "거래일자" -> date, "거래명" -> trade_name, "종목명" -> ticker_name
HEADER_ALIASES = {
    "거래일자": "date",
    "체결일자": "date",
    "일자": "date",
    "date": "date",

    "거래명": "trade_name",
    "적요": "trade_name",
    "내용": "trade_name",
    "trade_name": "trade_name",

    "종목명": "ticker_name",
    "종목": "ticker_name",
    "ticker_name": "ticker_name",

    "거래수량": "quantity",
    "수량": "quantity",
    "qty": "quantity",
    "quantity": "quantity",

    "거래단가": "price",
    "단가": "price",
    "price": "price",

    "거래금액": "amount",
    "금액": "amount",
    "amount": "amount",

    "정산금액": "settlement_amount",
    "settlement_amount": "settlement_amount",

    "수수료/fee": "fee",
    "수수료": "fee",
    "fee": "fee",

    "제세금/대출이자": "tax",
    "세금": "tax",
    "tax": "tax",

    "통화코드": "currency",
    "통화": "currency",
    "currency": "currency",

    "외화정산금액": "fx_settlement_amount",
    "외화거래금액": "fx_trade_amount",
    "외화예수금액": "fx_cash_balance",

    "거래번호": "trade_no",
    "현금잔액": "cash_balance",
    "잔고수량/펀드평가금액": "balance_quantity",
    "상대계좌명": "counterparty_name",
    "상대계좌번호": "counterparty_account",
    "처리점": "branch",
    "메모": "memo",
    "계좌": "account",
}

REQUIRED_COLUMNS = {"date", "trade_name"}


def _canon_header(value: Any) -> str:
    """
    헤더를 강하게 정규화한다.
    - 공백 제거
    - 줄바꿈 제거
    - 영문 소문자화
    - slash / underscore 유지
    """
    if value is None:
        return ""

    text = str(value).strip()
    text = text.replace("\n", "").replace("\r", "")
    text = re.sub(r"\s+", "", text)
    text = text.lower()

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


def _is_effective_empty_row(row: list[Any]) -> bool:
    for cell in row:
        if cell not in (None, "", "None"):
            return False
    return True


def parse_shinhan_xlsx(
    path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    try:
        rows = _read_sheet_rows(path)
    except Exception as exc:  # noqa: BLE001
        return [], [{"row": 0, "error": f"invalid xlsx: {exc}"}], {}

    if not rows:
        return [], [{"row": 0, "error": "empty file"}], {}

    raw_headers = rows[0]
    headers = [_canon_header(col) for col in raw_headers]
    header_index = {name: idx for idx, name in enumerate(headers) if name}

    missing = REQUIRED_COLUMNS - set(header_index.keys())
    if missing:
        return [], [{
            "row": 1,
            "error": f"missing required columns: {', '.join(sorted(missing))}",
            "raw_headers": [str(x) if x is not None else "" for x in raw_headers],
            "normalized_headers": headers,
        }], {}

    parsed: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    unknown_trade_names: dict[str, int] = {}

    for row_number, row in enumerate(rows[1:], start=2):
        if _is_effective_empty_row(row):
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
                "error": str(exc),
            })

    return parsed, errors, unknown_trade_names
