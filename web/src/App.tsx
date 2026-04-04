import { useEffect, useMemo, useState } from "react";
import { fetchEvents, fetchPortfolioSummary, uploadShinhanFile } from "./api";
import type {
  EventListResponse,
  PortfolioCashBucket,
  PortfolioPosition,
  PortfolioSummaryResponse,
  UploadShinhanResponse,
} from "./types";

type EventFilters = {
  ticker: string;
  event_type: string;
  currency: string;
  date_from: string;
  date_to: string;
  raw_trade_name: string;
};

const initialFilters: EventFilters = {
  ticker: "",
  event_type: "",
  currency: "",
  date_from: "",
  date_to: "",
  raw_trade_name: "",
};

function fmt(n: number | null | undefined) {
  if (n === null || n === undefined) return "-";
  return new Intl.NumberFormat("ko-KR", {
    maximumFractionDigits: 6,
  }).format(n);
}

function SummaryCards({ summary }: { summary: PortfolioSummaryResponse }) {
  const totalUsdCostBasis = summary.holding_cost_basis_by_currency["USD"] ?? 0;
  const totalKrwCash =
    summary.cash.find((c) => c.currency === "KRW")?.net_cash ?? 0;
  const totalUsdCash =
    summary.cash.find((c) => c.currency === "USD")?.net_cash ?? 0;

  return (
    <div className="card-grid">
      <div className="card">
        <div className="card-label">Holdings Count</div>
        <div className="card-value">{summary.holdings_count}</div>
      </div>
      <div className="card">
        <div className="card-label">Cash Buckets</div>
        <div className="card-value">{summary.cash_count}</div>
      </div>
      <div className="card">
        <div className="card-label">USD Cost Basis</div>
        <div className="card-value">{fmt(totalUsdCostBasis)}</div>
      </div>
      <div className="card">
        <div className="card-label">KRW Net Cash</div>
        <div className="card-value">{fmt(totalKrwCash)}</div>
      </div>
      <div className="card">
        <div className="card-label">USD Net Cash</div>
        <div className="card-value">{fmt(totalUsdCash)}</div>
      </div>
      <div className="card">
        <div className="card-label">Adjustments Applied</div>
        <div className="card-value">{summary.adjustments_applied.length}</div>
      </div>
    </div>
  );
}

function PositionsTable({ rows }: { rows: PortfolioPosition[] }) {
  return (
    <div className="section">
      <h2>Holdings</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Name</th>
              <th>Qty</th>
              <th>Avg Cost</th>
              <th>Cost Basis</th>
              <th>Currency</th>
              <th>Realized PnL</th>
              <th>Last Event</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.ticker}>
                <td>{row.ticker}</td>
                <td>{row.ticker_name || "-"}</td>
                <td>{fmt(row.quantity)}</td>
                <td>{fmt(row.avg_cost)}</td>
                <td>{fmt(row.cost_basis)}</td>
                <td>{row.currency || "-"}</td>
                <td>{fmt(row.realized_pnl)}</td>
                <td>{row.last_event_date || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CashTable({ rows }: { rows: PortfolioCashBucket[] }) {
  return (
    <div className="section">
      <h2>Cash</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Currency</th>
              <th>Net Cash</th>
              <th>Cash In</th>
              <th>Cash Out</th>
              <th>Buy Out</th>
              <th>Sell In</th>
              <th>Dividend</th>
              <th>Tax</th>
              <th>FX Buy In</th>
              <th>FX Sell Out</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.currency}>
                <td>{row.currency}</td>
                <td>{fmt(row.net_cash)}</td>
                <td>{fmt(row.cash_in)}</td>
                <td>{fmt(row.cash_out)}</td>
                <td>{fmt(row.buy_out)}</td>
                <td>{fmt(row.sell_in)}</td>
                <td>{fmt(row.dividend_in)}</td>
                <td>{fmt(row.tax_out)}</td>
                <td>{fmt(row.fx_buy_in)}</td>
                <td>{fmt(row.fx_sell_out)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AdjustmentsTable({
  rows,
}: {
  rows: PortfolioSummaryResponse["adjustments_applied"];
}) {
  return (
    <div className="section">
      <h2>Adjustments Applied</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Ticker</th>
              <th>Reason</th>
              <th>Event Qty</th>
              <th>Covered Qty</th>
              <th>Source Row</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={`${row.ticker}-${row.date}-${idx}`}>
                <td>{row.date || "-"}</td>
                <td>{row.ticker || "-"}</td>
                <td>{row.reason}</td>
                <td>{fmt(row.event_quantity)}</td>
                <td>{fmt(row.covered_qty)}</td>
                <td>{row.source_row_number ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function UploadSection({
  onUploadDone,
}: {
  onUploadDone: () => Promise<void>;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [forceReplace, setForceReplace] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [result, setResult] = useState<UploadShinhanResponse | null>(null);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();

    if (!file) {
      setUploadError("업로드할 파일을 먼저 선택해야 한다.");
      return;
    }

    setUploading(true);
    setUploadError("");
    setResult(null);

    try {
      const res = await uploadShinhanFile({
        file,
        forceReplace,
      });
      setResult(res);
      await onUploadDone();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="section">
      <h2>Upload Shinhan Ledger</h2>

      <form className="upload-form" onSubmit={handleUpload}>
        <input
          type="file"
          accept=".xlsx"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />

        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={forceReplace}
            onChange={(e) => setForceReplace(e.target.checked)}
          />
          <span>force_replace</span>
        </label>

        <button type="submit" disabled={uploading || !file}>
          {uploading ? "Uploading..." : "Upload"}
        </button>
      </form>

      {uploadError && <div className="error-box">{uploadError}</div>}

      {result && (
        <div className="upload-result">
          <div className="result-grid">
            <div className="mini-card">
              <div className="mini-label">filename</div>
              <div className="mini-value">{result.filename}</div>
            </div>
            <div className="mini-card">
              <div className="mini-label">parsed_count</div>
              <div className="mini-value">{result.parsed_count}</div>
            </div>
            <div className="mini-card">
              <div className="mini-label">inserted_count</div>
              <div className="mini-value">{result.inserted_count}</div>
            </div>
            <div className="mini-card">
              <div className="mini-label">mapped_count</div>
              <div className="mini-value">{result.mapped_count}</div>
            </div>
            <div className="mini-card">
              <div className="mini-label">error_count</div>
              <div className="mini-value">{result.error_count}</div>
            </div>
            <div className="mini-card">
              <div className="mini-label">deleted_existing_count</div>
              <div className="mini-value">{result.deleted_existing_count}</div>
            </div>
          </div>

          <div className="subtle upload-hash">file_hash: {result.file_hash}</div>

          <details className="details-block">
            <summary>parsed_preview_head</summary>
            <pre>{JSON.stringify(result.parsed_preview_head, null, 2)}</pre>
          </details>

          <details className="details-block">
            <summary>parsed_preview_tail</summary>
            <pre>{JSON.stringify(result.parsed_preview_tail, null, 2)}</pre>
          </details>

          {result.error_count > 0 && (
            <details className="details-block">
              <summary>errors</summary>
              <pre>{JSON.stringify(result.errors, null, 2)}</pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
}

function EventsSection({ refreshKey }: { refreshKey: number }) {
  const [filters, setFilters] = useState<EventFilters>(initialFilters);
  const [data, setData] = useState<EventListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onSearch(e?: React.FormEvent) {
    e?.preventDefault();
    setLoading(true);
    setError("");

    try {
      const result = await fetchEvents({
        limit: 100,
        offset: 0,
        ticker: filters.ticker,
        event_type: filters.event_type,
        currency: filters.currency,
        date_from: filters.date_from,
        date_to: filters.date_to,
        raw_trade_name: filters.raw_trade_name,
      });
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

    useEffect(() => {
    void onSearch();
  }, [refreshKey]);
  return (
    <div className="section">
      <h2>Events Explorer</h2>

      <form className="filters" onSubmit={onSearch}>
        <input
          placeholder="Ticker"
          value={filters.ticker}
          onChange={(e) =>
            setFilters((p) => ({
              ...p,
              ticker: e.target.value.toUpperCase(),
            }))
          }
        />
        <input
          placeholder="Event Type"
          value={filters.event_type}
          onChange={(e) => setFilters((p) => ({ ...p, event_type: e.target.value }))}
        />
        <input
          placeholder="Currency"
          value={filters.currency}
          onChange={(e) => setFilters((p) => ({ ...p, currency: e.target.value }))}
        />
        <input
          type="date"
          value={filters.date_from}
          onChange={(e) => setFilters((p) => ({ ...p, date_from: e.target.value }))}
        />
        <input
          type="date"
          value={filters.date_to}
          onChange={(e) => setFilters((p) => ({ ...p, date_to: e.target.value }))}
        />
        <input
          placeholder="raw_trade_name"
          value={filters.raw_trade_name}
          onChange={(e) =>
            setFilters((p) => ({ ...p, raw_trade_name: e.target.value }))
          }
        />
        <button type="submit" disabled={loading}>
          {loading ? "Loading..." : "Search"}
        </button>
      </form>

      {error && <div className="error-box">{error}</div>}

      {data && (
        <>
          <div className="subtle">
            count: {data.count} / limit: {data.limit}
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Type</th>
                  <th>Ticker</th>
                  <th>Name</th>
                  <th>Qty</th>
                  <th>Price</th>
                  <th>Amount</th>
                  <th>Currency</th>
                  <th>Trade No</th>
                  <th>Raw Trade Name</th>
                </tr>
              </thead>
              <tbody>
                {data.events.map((row) => (
                  <tr key={row.id}>
                    <td>{row.date}</td>
                    <td>{row.event_type}</td>
                    <td>{row.ticker || "-"}</td>
                    <td>{row.ticker_name || "-"}</td>
                    <td>{fmt(row.quantity)}</td>
                    <td>{fmt(row.price)}</td>
                    <td>{fmt(row.amount)}</td>
                    <td>{row.currency || "-"}</td>
                    <td>{row.trade_no || "-"}</td>
                    <td>{row.raw_trade_name || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

export default function App() {
  const [eventsRefreshKey, setEventsRefreshKey] = useState(0);
  const [summary, setSummary] = useState<PortfolioSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function handleUploadDone() {
  await loadSummary();
  setEventsRefreshKey((v) => v + 1);
}
  
  async function loadSummary() {
    setLoading(true);
    setError(""); 

    try {
      const data = await fetchPortfolioSummary();
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadSummary();
  }, []);

  const title = useMemo(() => "StockiTrade", []);

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>{title}</h1>
          <p className="subtle">
            Read-only dashboard for portfolio / cash / uploads / events
          </p>
        </div>
      </header>

      {loading && <div className="panel">Loading...</div>}
      {error && <div className="error-box">{error}</div>}

      <UploadSection onUploadDone={handleUploadDone} />

      {summary && (
        <>
          <SummaryCards summary={summary} />
          <PositionsTable rows={summary.positions} />
          <CashTable rows={summary.cash} />
          <AdjustmentsTable rows={summary.adjustments_applied} />
        </>
      )}

      <EventsSection refreshKey={eventsRefreshKey} />
    </div>
  );
}
