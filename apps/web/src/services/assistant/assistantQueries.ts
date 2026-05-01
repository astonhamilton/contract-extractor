import {
  type AssistantApiQuery,
  getAssistantThreadItems,
  getAssistantThreads,
} from "@/services/assistant/assistantApi";

export const assistantKeys = {
  all: ["assistant"] as const,
  threads: () => [...assistantKeys.all, "threads"] as const,
  threadItems: (threadId: string) =>
    [...assistantKeys.all, "threads", threadId, "items"] as const,
};

export const assistantQueries = {
  threads: (query: AssistantApiQuery = {}) => ({
    queryKey: assistantKeys.threads(),
    queryFn: ({ signal }: { signal: AbortSignal }) =>
      getAssistantThreads({
        ...query,
        signal,
      }),
  }),
  threadItems: (threadId: string, query: AssistantApiQuery = {}) => ({
    queryKey: assistantKeys.threadItems(threadId),
    queryFn: ({ signal }: { signal: AbortSignal }) =>
      getAssistantThreadItems(threadId, {
        ...query,
        signal,
      }),
    enabled: threadId.length > 0,
  }),
};
