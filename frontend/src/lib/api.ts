// Use relative URL so requests go through Next.js rewrites (which proxy to backend).
// This fixes deployment issues where localhost:8000 is unreachable from the browser.
// Falls back to NEXT_PUBLIC_API_URL if explicitly set (e.g. for local dev pointing at a specific backend).
const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

export interface User {
  id: string;
  email: string;
  api_key: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UploadSession {
  id: string;
  filename: string;
  file_size: number;
  chunk_size: number;
  chunk_count: number;
  uploaded_chunks: number[];
  status: string;
  chunk_urls?: { chunk_index: number; upload_url: string }[];
}

export interface ValidationJob {
  id: string;
  upload_session_id: string;
  dataset_type: string;
  rule_set: string;
  status: string;
  progress: number;
  error_message: string | null;
  stats: Record<string, unknown> | null;
  output_files: {
    id: string;
    file_type: string;
    filename: string;
    file_size: number;
    download_url: string | null;
    row_count: number | null;
  }[];
}

export interface RuleSet {
  id: string;
  name: string;
  description: string;
  dataset_types: string[];
}

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('token');
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || JSON.stringify(err));
  }
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request<TokenResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, password: string) =>
    request<User>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<User>('/api/v1/auth/me'),

  listRuleSets: () => request<RuleSet[]>('/api/v1/rule-sets'),

  createUploadSession: (filename: string, fileSize: number, chunkSize?: number) =>
    request<UploadSession>('/api/v1/upload-sessions', {
      method: 'POST',
      body: JSON.stringify({ filename, file_size: fileSize, chunk_size: chunkSize }),
    }),

  markChunkComplete: (sessionId: string, chunkIndex: number) =>
    request(`/api/v1/upload-sessions/${sessionId}/chunks/${chunkIndex}/complete`, {
      method: 'POST',
    }),

  completeUpload: (sessionId: string) =>
    request<UploadSession>(`/api/v1/upload-sessions/${sessionId}/complete`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  createValidationJob: (uploadSessionId: string, datasetType: string, ruleSet: string, options?: object) =>
    request<ValidationJob>('/api/v1/validation-jobs', {
      method: 'POST',
      body: JSON.stringify({
        upload_session_id: uploadSessionId,
        dataset_type: datasetType,
        rule_set: ruleSet,
        options: options || {},
      }),
    }),

  getValidationJob: (jobId: string) => request<ValidationJob>(`/api/v1/validation-jobs/${jobId}`),

  listValidationJobs: () =>
    request<{ id: string; dataset_type: string; status: string; progress: number; created_at: string }[]>(
      '/api/v1/validation-jobs'
    ),
};

export async function uploadFileChunked(
  file: File,
  onProgress: (pct: number, message: string) => void
): Promise<UploadSession> {
  const chunkSize = 5 * 1024 * 1024;
  const session = await api.createUploadSession(file.name, file.size, chunkSize);
  const urls = session.chunk_urls || [];

  for (let i = 0; i < session.chunk_count; i++) {
    const start = i * session.chunk_size;
    const end = Math.min(start + session.chunk_size, file.size);
    const chunk = file.slice(start, end);
    const urlInfo = urls.find((u) => u.chunk_index === i);
    if (!urlInfo) throw new Error(`Missing upload URL for chunk ${i}`);

    onProgress(Math.round((i / session.chunk_count) * 80), `Uploading chunk ${i + 1}/${session.chunk_count}...`);

    const res = await fetch(urlInfo.upload_url, {
      method: 'PUT',
      body: chunk,
      headers: { 'Content-Type': file.type || 'application/octet-stream' },
    });
    if (!res.ok) throw new Error(`Chunk ${i} upload failed: ${res.statusText}`);

    await api.markChunkComplete(session.id, i);
  }

  onProgress(90, 'Finalizing upload...');
  return api.completeUpload(session.id);
}
