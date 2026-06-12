import { z } from 'zod';

// ─── Intent & Category ────────────────────────────────────────────────────────

export const INTENTS = [
  'FIND_LAW',
  'FIND_SECTION',
  'FIND_CASE',
  'EXPLAIN_RIGHTS',
  'CHECK_PROCESS',
  'COMPARE_LAWS',
  'GET_DOCUMENT',
  'GENERAL_INFO',
  'UNKNOWN',
] as const;
export type Intent = (typeof INTENTS)[number];

export const CATEGORIES = [
  'criminal',
  'civil',
  'family',
  'land_property',
  'labor_employment',
  'constitutional',
  'commercial_business',
  'banking_finance',
  'tenancy_rent',
  'consumer_rights',
  'digital_cyber',
  'immigration',
] as const;
export type Category = (typeof CATEGORIES)[number];

export const IntentDataSchema = z.object({
  intent: z.string(),
  category: z.string(),
  confidence: z.number(),
  language: z.enum(['bn', 'en', 'mixed']),
  stage: z.number(),
});
export type IntentData = z.infer<typeof IntentDataSchema>;

// ─── Sources ──────────────────────────────────────────────────────────────────

export const SourceItemSchema = z.object({
  source_type: z.enum(['section', 'case']),
  relevance_score: z.number(),
  act_title_en: z.string().optional(),
  act_id: z.string().optional(),
  category: z.string().optional(),
  year: z.number().nullable().optional(),
  section_number: z.string().nullable().optional(),
  section_title: z.string().nullable().optional(),
  content_en: z.string().nullable().optional(),
  content_bn: z.string().nullable().optional(),
  citation: z.string().nullable().optional(),
  court: z.string().nullable().optional(),
  parties: z.string().nullable().optional(),
  summary: z.string().nullable().optional(),
});
export type SourceItem = z.infer<typeof SourceItemSchema>;

// ─── SSE Events ───────────────────────────────────────────────────────────────

export const SSEIntentEventSchema = z.object({
  type: z.literal('intent'),
  data: IntentDataSchema,
});

export const SSESourcesEventSchema = z.object({
  type: z.literal('sources'),
  data: z.array(SourceItemSchema),
});

export const SSETokenEventSchema = z.object({
  type: z.literal('token'),
  data: z.string(),
});

export const SSEErrorEventSchema = z.object({
  type: z.literal('error'),
  data: z.object({
    message: z.string(),
    code: z.string().optional(),
  }),
});

export const SSEDoneEventSchema = z.object({
  type: z.literal('done'),
  data: z.object({
    message_id: z.string(),
    response_time_ms: z.number(),
    intent: z.string(),
    category: z.string(),
    sources_count: z.number(),
    strategy: z.string(),
    full_response: z.string(),
  }),
});
export type SSEDoneData = z.infer<typeof SSEDoneEventSchema>['data'];

export const SSECitationsEventSchema = z.object({
  type: z.literal('citations'),
  data: z.array(z.object({
    law_name:  z.string(),
    section:   z.string(),
    title:     z.string(),
    relevance: z.number(),
  })),
});

export const SSEEventSchema = z.discriminatedUnion('type', [
  SSEIntentEventSchema,
  SSESourcesEventSchema,
  SSECitationsEventSchema,
  SSETokenEventSchema,
  SSEErrorEventSchema,
  SSEDoneEventSchema,
]);
export type SSEEvent = z.infer<typeof SSEEventSchema>;

// ─── API Responses ────────────────────────────────────────────────────────────

export const SessionResponseSchema = z.object({
  id: z.string().uuid(),
  title: z.string().nullable(),
  created_at: z.string(),
  message_count: z.number().default(0),
});
export type SessionResponse = z.infer<typeof SessionResponseSchema>;

export const MessageResponseSchema = z.object({
  id: z.string().uuid(),
  role: z.enum(['user', 'assistant']),
  content: z.string(),
  intent: z.string().nullable(),
  category: z.string().nullable(),
  sources: z.array(SourceItemSchema).nullable(),
  created_at: z.string(),
});
export type MessageResponse = z.infer<typeof MessageResponseSchema>;

export const SessionDetailResponseSchema = SessionResponseSchema.omit({
  message_count: true,
}).extend({
  messages: z.array(MessageResponseSchema),
});
export type SessionDetailResponse = z.infer<typeof SessionDetailResponseSchema>;

// ─── Citations ────────────────────────────────────────────────────────────────

export interface CitationSource {
  law_name:  string;
  section:   string;
  title:     string;
  relevance: number;
}

// ─── Chat Store ───────────────────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: IntentData;
  sources?: SourceItem[];
  citations?: CitationSource[];
  isStreaming: boolean;
  error?: string;
  timestamp: Date;
}

// ─── Stream Handlers ──────────────────────────────────────────────────────────

export interface ChatStreamHandlers {
  onIntent?:    (data: IntentData) => void;
  onSources?:   (data: SourceItem[]) => void;
  onCitations?: (data: CitationSource[]) => void;
  onToken?:     (token: string) => void;
  onDone?:      (data: SSEDoneData) => void;
  onError?:     (message: string) => void;
}

// ─── NextAuth session extension ───────────────────────────────────────────────

declare module 'next-auth' {
  interface Session {
    accessToken?: string;
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    accessToken?: string;
  }
}
