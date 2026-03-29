from fastapi.testclient import TestClient

from app.main import app
from app.routers import portfolio as portfolio_router


client = TestClient(app)


def test_portfolio_summary_response_shape(monkeypatch):
    fake_summary = {
        "holdings_count": 1,
        "cash_count": 1,
        "positions": [
            {
                "ticker": "ANET",
                "ticker_name": "USD 아리스타 네트웍스",
                "quantity": 5,
                "avg_cost": 136.4,
                "cost_basis": 682.0,
                "market": "US",
                "asset_type": "stock",
                "currency": "USD",
                "realized_pnl": 0.0,
                "last_event_date": "2026-03-03",
            }
        ],
        "cash": [
            {
                "currency": "USD",
                "net_cash": 703.657297,
                "cash_in": 262.94,
                "cash_out": 0.0,
                "buy_out": 12260.782499,
                "sell_in": 9545.569797,
                "dividend_in": 9.91,
                "tax_out": 1.28,
                "fx_buy_out": 0.0,
                "fx_buy_in": 3735.75,
                "fx_sell_out": 588.45,
                "fx_sell_in": 0.0,
                "fx_pnl_adjust": 0.0,
            }
        ],
        "realized_pnl_by_currency": {"USD": 566.013964, "KRW": -3662.0},
        "open_positions_realized_pnl_by_currency": {"USD": 0.0},
        "position_count_by_currency": {"USD": 1},
        "holding_cost_basis_by_currency": {"USD": 682.0},
        "anomalies": [],
        "adjustments_applied": [
            {
                "ticker": "SOXL",
                "date": "2025-08-18",
                "reason": "sell_before_buy_same_day_compensated",
                "event_quantity": 12,
                "covered_qty": 12,
                "source_row_number": 8,
            }
        ],
    }

    monkeypatch.setattr(portfolio_router, "build_portfolio_summary", lambda: fake_summary)

    response = client.get("/portfolio/summary")
    assert response.status_code == 200

    data = response.json()
    assert data["holdings_count"] == 1
    assert data["cash_count"] == 1
    assert isinstance(data["positions"], list)
    assert isinstance(data["cash"], list)
    assert isinstance(data["anomalies"], list)
    assert isinstance(data["adjustments_applied"], list)
    assert data["adjustments_applied"][0]["reason"] == "sell_before_buy_same_day_compensated"


def test_portfolio_cash_response_shape(monkeypatch):
    fake_cash = {
        "count": 2,
        "cash": [
            {
                "currency": "KRW",
                "net_cash": 149680.0,
                "cash_in": 6819603.0,
                "cash_out": 2176478.0,
                "buy_out": 264838.0,
                "sell_in": 261176.0,
                "dividend_in": 3.0,
                "tax_out": 0.0,
                "fx_buy_out": 5337422.0,
                "fx_buy_in": 0.0,
                "fx_sell_out": 0.0,
                "fx_sell_in": 832166.0,
                "fx_pnl_adjust": 15470.0,
            },
            {
                "currency": "USD",
                "net_cash": 703.657297,
                "cash_in": 262.94,
                "cash_out": 0.0,
                "buy_out": 12260.782499,
                "sell_in": 9545.569797,
                "dividend_in": 9.91,
                "tax_out": 1.28,
                "fx_buy_out": 0.0,
                "fx_buy_in": 3735.75,
                "fx_sell_out": 588.45,
                "fx_sell_in": 0.0,
                "fx_pnl_adjust": 0.0,
            },
        ],
        "anomalies": [],
        "adjustments_applied": [],
    }

    monkeypatch.setattr(portfolio_router, "build_portfolio_cash", lambda: fake_cash)

    response = client.get("/portfolio/cash")
    assert response.status_code == 200

    data = response.json()
    assert data["count"] == 2
    assert len(data["cash"]) == 2
    assert data["anomalies"] == []
    assert data["adjustments_applied"] == []


def test_portfolio_holdings_response_shape(monkeypatch):
    fake_holdings = {
        "count": 2,
        "holdings": [
            {
                "ticker": "ANET",
                "ticker_name": "USD 아리스타 네트웍스",
                "quantity": 5,
                "avg_cost": 136.4,
                "cost_basis": 682.0,
                "market": "US",
                "asset_type": "stock",
                "currency": "USD",
                "realized_pnl": 0.0,
                "last_event_date": "2026-03-03",
            },
            {
                "ticker": "MU",
                "ticker_name": "USD 마이크론 테크놀로지",
                "quantity": 2,
                "avg_cost": 245.663333,
                "cost_basis": 491.326667,
                "market": "US",
                "asset_type": "stock",
                "currency": "USD",
                "realized_pnl": 353.866667,
                "last_event_date": "2026-03-11",
            },
        ],
        "realized_pnl_by_currency": {"USD": 353.866667},
        "anomalies": [],
        "adjustments_applied": [
            {
                "ticker": "UVIX",
                "date": "2026-03-04",
                "reason": "sell_before_buy_same_day_compensated",
                "event_quantity": 12,
                "covered_qty": 12,
                "source_row_number": 202,
            }
        ],
    }

    monkeypatch.setattr(portfolio_router, "build_portfolio_holdings", lambda: fake_holdings)

    response = client.get("/portfolio/holdings")
    assert response.status_code == 200

    data = response.json()
    assert data["count"] == 2
    assert len(data["holdings"]) == 2
    assert data["anomalies"] == []
    assert data["adjustments_applied"][0]["ticker"] == "UVIX"
