import type { EventListResponse, PortfolioSummaryResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://api.stockitrade.com";

async function request<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }

  return res.json() as Promise<T>;
}

export async function fetchPortfolioSummary(): Promise<PortfolioSummaryResponse> {
  return request<PortfolioSummaryResponse>("/portfolio/summary");
}

export async function fetchEvents(params: {
  limit?: number;
  offset?: number;
  ticker?: string;
  event_type?: string;
  currency?: string;
  date_from?: string;
  date_to?: string;
  raw_trade_name?: string;
  file_hash?: string;
}): Promise<EventListResponse> {
  const search = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      if (key === "ticker") {
        search.set(key, String(value).trim().toUpperCase());
      } else {
        search.set(key, String(value).trim());
      }
    }
  });

  return request<EventListResponse>(`/events?${search.toString()}`);
}
