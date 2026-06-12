import axios from 'axios';
import { z } from 'zod';
import {
  SessionResponseSchema,
  SessionDetailResponseSchema,
  SSEEventSchema,
  type ChatStreamHandlers,
} from '@/types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15_000,
});

function authHeader(token: string | undefined): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
  phone?: string | null;
}

export interface AuthUser {
  id: string;
  email: string;
  name: string | null;
  role: string;
  plan: string;
  query_count_today: number;
  query_limit: number;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export async function authRegister(payload: RegisterPayload): Promise<AuthTokenResponse> {
  const { data } = await apiClient.post<AuthTokenResponse>('/api/auth/register', payload);
  return data;
}

export interface UserProfile {
  id: string;
  email: string;
  name: string | null;
  phone: string | null;
  role: string;
  plan: string;
  query_count_today: number;
  query_limit: number;
  created_at: string | null;
}

export async function getMe(token: string | undefined): Promise<UserProfile> {
  const { data } = await apiClient.get<UserProfile>('/api/auth/me', {
    headers: authHeader(token),
  });
  return data;
}

export interface UpdateProfilePayload {
  name?: string;
  phone?: string | null;
}

export async function updateProfile(
  payload: UpdateProfilePayload,
  token: string | undefined,
): Promise<UserProfile> {
  const { data } = await apiClient.put<UserProfile>('/api/auth/profile', payload, {
    headers: authHeader(token),
  });
  return data;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export async function changePassword(
  payload: ChangePasswordPayload,
  token: string | undefined,
): Promise<void> {
  await apiClient.put('/api/auth/password', payload, {
    headers: authHeader(token),
  });
}

// ─── Sessions ─────────────────────────────────────────────────────────────────

export async function createSession(
  token: string | undefined,
  title?: string,
) {
  const { data } = await apiClient.post(
    '/api/chat/sessions',
    { title: title ?? null },
    { headers: authHeader(token) },
  );
  return SessionResponseSchema.parse(data);
}

export async function listSessions(token: string | undefined) {
  const { data } = await apiClient.get('/api/chat/sessions', {
    headers: authHeader(token),
  });
  return z.array(SessionResponseSchema).parse(data);
}

export async function getSession(id: string, token: string | undefined) {
  const { data } = await apiClient.get(`/api/chat/sessions/${id}`, {
    headers: authHeader(token),
  });
  return SessionDetailResponseSchema.parse(data);
}

// ─── Shared SSE stream reader ─────────────────────────────────────────────────

async function _readSSEStream(
  response: Response,
  handlers: ChatStreamHandlers,
): Promise<void> {
  if (!response.body) throw new Error('No response body from server');

  const reader  = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer    = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const raw = line.slice(6).trim();
        if (!raw) continue;

        let parsed: unknown;
        try {
          parsed = JSON.parse(raw);
        } catch {
          continue;
        }

        const result = SSEEventSchema.safeParse(parsed);
        if (!result.success) continue;

        const event = result.data;
        switch (event.type) {
          case 'intent':    handlers.onIntent?.(event.data);            break;
          case 'sources':   handlers.onSources?.(event.data);           break;
          case 'citations': handlers.onCitations?.(event.data);         break;
          case 'token':     handlers.onToken?.(event.data);             break;
          case 'done':      handlers.onDone?.(event.data);              break;
          case 'error':     handlers.onError?.(event.data.message);     break;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function _httpError(response: Response, body: unknown): Error {
  const detail =
    body !== null &&
    typeof body === 'object' &&
    'detail' in body &&
    typeof (body as Record<string, unknown>).detail === 'string'
      ? (body as Record<string, string>).detail
      : `HTTP ${response.status}`;
  return new Error(detail);
}

// ─── SSE Chat Stream ──────────────────────────────────────────────────────────

export async function streamChat(
  params: { query: string; sessionId: string | null; language?: string },
  token: string | undefined,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader(token) },
    body: JSON.stringify({ query: params.query, session_id: params.sessionId ?? null, language: params.language ?? 'bn' }),
    signal,
  });

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    throw _httpError(response, body);
  }

  await _readSSEStream(response, handlers);
}

// ─── Image Vision Analysis ────────────────────────────────────────────────────

export interface ImageAnalysisResult {
  analysis: string;
  detected_type: string;
  language: string;
}

export async function analyzeImage(file: File, language: string): Promise<ImageAnalysisResult> {
  const formData = new FormData();
  formData.append('image', file);
  formData.append('language', language);

  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const response = await fetch(`${BASE_URL}/api/documents/analyze-image`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    throw _httpError(response, body);
  }

  return response.json() as Promise<ImageAnalysisResult>;
}

// ─── Document vision analysis stream ─────────────────────────────────────────

export async function analyzeDocument(
  params: { file: File; query: string; sessionId: string | null },
  token: string | undefined,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const form = new FormData();
  form.append('file', params.file);
  form.append('query', params.query);
  if (params.sessionId) form.append('session_id', params.sessionId);

  // Do NOT set Content-Type — the browser sets it with the correct multipart boundary
  const response = await fetch(`${BASE_URL}/api/chat/analyze-document`, {
    method: 'POST',
    headers: authHeader(token),
    body: form,
    signal,
  });

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    throw _httpError(response, body);
  }

  await _readSSEStream(response, handlers);
}
