export type PortfolioPosition = {
  ticker: string;
  ticker_name?: string | null;
  quantity: number;
  avg_cost: number;
  cost_basis: number;
  market?: string | null;
  asset_type?: string | null;
  currency?: string | null;
  realized_pnl: number;
  last_event_date?: string | null;
};

export type PortfolioCashBucket = {
  currency: string;
  net_cash: number;
  cash_in: number;
  cash_out: number;
  buy_out: number;
  sell_in: number;
  dividend_in: number;
  tax_out: number;
  fx_buy_out: number;
  fx_buy_in: number;
  fx_sell_out: number;
  fx_sell_in: number;
  fx_pnl_adjust: number;
};

export type PortfolioAdjustmentApplied = {
  ticker?: string | null;
  date?: string | null;
  reason: string;
  event_quantity?: number | null;
  covered_qty?: number | null;
  source_row_number?: number | null;
};

export type PortfolioAnomaly = {
  ticker?: string | null;
  date?: string | null;
  reason: string;
  event_quantity?: number | null;
  position_quantity?: number | null;
  cost_basis?: number | null;
  raw_trade_name?: string | null;
  source_row_number?: number | null;
};

export type PortfolioSummaryResponse = {
  holdings_count: number;
  cash_count: number;
  positions: PortfolioPosition[];
  cash: PortfolioCashBucket[];
  realized_pnl_by_currency: Record<string, number>;
  open_positions_realized_pnl_by_currency: Record<string, number>;
  position_count_by_currency: Record<string, number>;
  holding_cost_basis_by_currency: Record<string, number>;
  anomalies: PortfolioAnomaly[];
  adjustments_applied: PortfolioAdjustmentApplied[];
};

export type EventRecord = {
  id: number;
  date: string;
  event_type: string;
  ticker?: string | null;
  ticker_name?: string | null;
  quantity?: number | null;
  price?: number | null;
  amount?: number | null;
  fee: number;
  tax: number;
  currency?: string | null;
  account?: string | null;
  memo?: string | null;
  raw_trade_name?: string | null;
  trade_no?: string | null;
  source_broker?: string | null;
  source_row_number?: number | null;
  market?: string | null;
  asset_type?: string | null;
  mapping_status?: string | null;
  file_hash?: string | null;
  created_at?: string | null;
};

export type EventListResponse = {
  count: number;
  limit: number;
  offset: number;
  applied_filters: Record<string, string | null>;
  events: EventRecord[];
};

export type UploadPreviewEvent = {
  event_type: string;
  date: string;
  ticker?: string | null;
  ticker_name?: string | null;
  quantity?: number | null;
  price?: number | null;
  amount?: number | null;
  fee: number;
  tax: number;
  currency?: string | null;
  raw_trade_name?: string | null;
  trade_no?: string | null;
  source_row_number?: number | null;
  market?: string | null;
  asset_type?: string | null;
  mapping_status?: string | null;
};

export type UploadShinhanResponse = {
  message: string;
  filename: string;
  saved_path: string;
  file_hash: string;
  force_replace: boolean;
  deleted_existing_count: number;
  parsed_count: number;
  inserted_count: number;
  mapped_count: number;
  unmapped_name_count: number;
  error_count: number;
  errors: Array<Record<string, unknown>>;
  unknown_trade_names: Record<string, number>;
  unmapped_name_priorities: Array<Record<string, unknown>>;
  parsed_preview_head: UploadPreviewEvent[];
  parsed_preview_tail: UploadPreviewEvent[];
};
