import type {
  EventListResponse,
  PortfolioSummaryResponse,
  UploadShinhanResponse,
} from "./types";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://api.stockitrade.com";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      Accept: "application/json",
      ...(init?.headers || {}),
    },
    ...init,
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

export async function uploadShinhanFile(args: {
  file: File;
  forceReplace: boolean;
}): Promise<UploadShinhanResponse> {
  const { file, forceReplace } = args;

  const search = new URLSearchParams({
    filename: file.name,
    force_replace: String(forceReplace),
  });

  const body = await file.arrayBuffer();

  return request<UploadShinhanResponse>(`/uploads/shinhan?${search.toString()}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/octet-stream",
    },
    body,
  });
}
