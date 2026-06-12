import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { ChatMessage, CitationSource, IntentData, SourceItem } from '@/types';

interface ChatState {
  messages: ChatMessage[];
  sessionId: string | null;
  isStreaming: boolean;

  startUserTurn: (content: string) => void;
  startAssistantStream: () => string;
  setMessageIntent: (id: string, intent: IntentData) => void;
  setMessageSources: (id: string, sources: SourceItem[]) => void;
  setMessageCitations: (id: string, citations: CitationSource[]) => void;
  appendToken: (id: string, token: string) => void;
  finishStream: (id: string) => void;
  setError: (id: string, message: string) => void;
  setSessionId: (id: string) => void;
  reset: () => void;
}

const INITIAL: Pick<ChatState, 'messages' | 'sessionId' | 'isStreaming'> = {
  messages: [],
  sessionId: null,
  isStreaming: false,
};

function newId(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export const useChatStore = create<ChatState>()(
  devtools(
    (set) => ({
      ...INITIAL,

      startUserTurn: (content) =>
        set((state) => ({
          messages: [
            ...state.messages,
            {
              id: newId(),
              role: 'user' as const,
              content,
              isStreaming: false,
              timestamp: new Date(),
            },
          ],
        })),

      startAssistantStream: () => {
        const id = newId();
        set((state) => ({
          isStreaming: true,
          messages: [
            ...state.messages,
            {
              id,
              role: 'assistant' as const,
              content: '',
              isStreaming: true,
              timestamp: new Date(),
            },
          ],
        }));
        return id;
      },

      setMessageIntent: (id, intent) =>
        set((state) => ({
          messages: state.messages.map((m) =>
            m.id === id ? { ...m, intent } : m,
          ),
        })),

      setMessageSources: (id, sources) =>
        set((state) => ({
          messages: state.messages.map((m) =>
            m.id === id ? { ...m, sources } : m,
          ),
        })),

      setMessageCitations: (id, citations) =>
        set((state) => ({
          messages: state.messages.map((m) =>
            m.id === id ? { ...m, citations } : m,
          ),
        })),

      appendToken: (id, token) =>
        set((state) => ({
          messages: state.messages.map((m) =>
            m.id === id ? { ...m, content: m.content + token } : m,
          ),
        })),

      finishStream: (id) =>
        set((state) => ({
          isStreaming: false,
          messages: state.messages.map((m) =>
            m.id === id ? { ...m, isStreaming: false } : m,
          ),
        })),

      setError: (id, message) =>
        set((state) => ({
          isStreaming: false,
          messages: state.messages.map((m) =>
            m.id === id
              ? { ...m, isStreaming: false, error: message, content: message }
              : m,
          ),
        })),

      setSessionId: (id) => set({ sessionId: id }),

      reset: () => set(INITIAL),
    }),
    { name: 'ai-lawyer-chat' },
  ),
);
