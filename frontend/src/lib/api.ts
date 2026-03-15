const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  token?: string | null;
};

class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {}, token } = options;

  const requestHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...headers,
  };

  if (token) {
    requestHeaders["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    method,
    headers: requestHeaders,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      errorData?.detail || `Request failed with status ${response.status}`,
      errorData
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ── Auth ──────────────────────────────────────────
export const auth = {
  signup: (data: { email: string; password: string; name: string }) =>
    request<{ access_token: string; refresh_token: string }>("/api/v1/auth/signup", {
      method: "POST",
      body: data,
    }),

  login: (data: { email: string; password: string }) =>
    request<{ access_token: string; refresh_token: string }>("/api/v1/auth/login", {
      method: "POST",
      body: data,
    }),

  refresh: (refreshToken: string) =>
    request<{ access_token: string; refresh_token: string }>("/api/v1/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
    }),

  me: (token: string) =>
    request<{
      id: string;
      email: string;
      name: string;
      avatar_url: string | null;
      role: string;
      default_cloud: string;
      default_iac: string;
      tenant_id: string;
    }>("/api/v1/auth/me", { token }),
};

// ── Projects ──────────────────────────────────────
export interface Project {
  id: string;
  name: string;
  description: string | null;
  cloud_provider: string;
  iac_tool: string;
  region: string;
  tags: string[];
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export const projects = {
  list: (token: string) =>
    request<Project[]>("/api/v1/projects", { token }),

  create: (token: string, data: { name: string; description?: string; cloud_provider?: string; iac_tool?: string; region?: string }) =>
    request<Project>("/api/v1/projects", { method: "POST", body: data, token }),

  get: (token: string, id: string) =>
    request<Project>(`/api/v1/projects/${id}`, { token }),

  update: (token: string, id: string, data: Partial<Project>) =>
    request<Project>(`/api/v1/projects/${id}`, { method: "PUT", body: data, token }),

  delete: (token: string, id: string) =>
    request<void>(`/api/v1/projects/${id}`, { method: "DELETE", token }),
};

export { ApiError };
