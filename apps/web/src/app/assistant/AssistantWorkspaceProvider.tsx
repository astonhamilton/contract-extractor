import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  assistantThreadSummaryFromApiItem,
} from "@/screens/AssistantScreen/AssistantScreen.adapters";
import { mergeThreadSummaries } from "@/screens/AssistantScreen/AssistantScreen.threadState";
import type { AssistantThread } from "@/screens/AssistantScreen/AssistantScreen.types";
import { assistantKeys, assistantQueries } from "@/services/assistant/assistantQueries";
import { useStoredState } from "@/lib/useStoredState";

type AssistantWorkspaceContextValue = {
  createDraftThread: () => AssistantThread;
  refreshThreads: () => Promise<void>;
  replaceDraftWithBackendThread: (
    draftThreadId: string,
    backendThread: AssistantThread,
  ) => void;
  selectThread: (threadId: string) => void;
  selectedThread: AssistantThread | null;
  selectedThreadId: string | null;
  threads: AssistantThread[];
  threadsError: string | null;
  threadsLoading: boolean;
  threadsRefreshing: boolean;
  updateThread: (
    threadId: string,
    updater: (thread: AssistantThread) => AssistantThread,
  ) => void;
};

const AssistantWorkspaceContext =
  createContext<AssistantWorkspaceContextValue | null>(null);

type AssistantWorkspaceProviderProps = {
  children: ReactNode;
};

function makeDraftThread(): AssistantThread {
  return {
    id: `draft-${Date.now()}`,
    backendThreadId: null,
    title: "New thread",
    summary: "Send the first message to start this thread.",
    status: "draft",
    updatedAt: "just now",
    messages: [],
    isDraft: true,
    itemsLoaded: true,
  };
}

export function AssistantWorkspaceProvider({
  children,
}: AssistantWorkspaceProviderProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const selectedThreadId = searchParams.get("thread");
  const [draftThreads, setDraftThreads] = useStoredState<AssistantThread[]>(
    "ci.assistant.draftThreads",
    [],
    { storage: "session" },
  );
  const [backendThreads, setBackendThreads] = useState<AssistantThread[]>([]);
  const threadsQuery = useQuery(assistantQueries.threads());

  useEffect(() => {
    if (!threadsQuery.data) {
      return;
    }
    const nextSummaries = threadsQuery.data.items.map(assistantThreadSummaryFromApiItem);
    setBackendThreads((current) => mergeThreadSummaries(current, nextSummaries));
  }, [threadsQuery.data]);

  const threads = useMemo(
    () => [...draftThreads, ...backendThreads],
    [backendThreads, draftThreads],
  );
  const selectedThread = useMemo(
    () => threads.find((thread) => thread.id === selectedThreadId) ?? null,
    [selectedThreadId, threads],
  );

  const selectThread = useCallback(
    (threadId: string) => {
      navigate(`/assistant?thread=${encodeURIComponent(threadId)}`);
    },
    [navigate],
  );

  const createDraftThread = useCallback(() => {
    const thread = makeDraftThread();
    setDraftThreads((current) => [thread, ...current]);
    navigate(`/assistant?thread=${encodeURIComponent(thread.id)}`);
    return thread;
  }, [navigate, setDraftThreads]);

  const updateThread = useCallback(
    (threadId: string, updater: (thread: AssistantThread) => AssistantThread) => {
      const applyUpdate = (current: AssistantThread[]): AssistantThread[] => {
        let changed = false;
        const next = current.map((thread) => {
          if (thread.id !== threadId) {
            return thread;
          }
          const updated = updater(thread);
          if (updated !== thread) {
            changed = true;
          }
          return updated;
        });
        return changed ? next : current;
      };
      setDraftThreads(applyUpdate);
      setBackendThreads(applyUpdate);
    },
    [setDraftThreads],
  );

  const replaceDraftWithBackendThread = useCallback(
    (draftThreadId: string, backendThread: AssistantThread) => {
      setDraftThreads((current) =>
        current.filter((thread) => thread.id !== draftThreadId),
      );
      setBackendThreads((current) => [
        backendThread,
        ...current.filter((thread) => thread.id !== backendThread.id),
      ]);
      navigate(`/assistant?thread=${encodeURIComponent(backendThread.id)}`, {
        replace: true,
      });
    },
    [navigate, setDraftThreads],
  );

  const refreshThreads = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: assistantKeys.threads() });
    await threadsQuery.refetch();
  }, [queryClient, threadsQuery]);

  const value = useMemo<AssistantWorkspaceContextValue>(
    () => ({
      createDraftThread,
      refreshThreads,
      replaceDraftWithBackendThread,
      selectThread,
      selectedThread,
      selectedThreadId,
      threads,
      threadsError:
        threadsQuery.error instanceof Error
          ? threadsQuery.error.message
          : threadsQuery.isError
            ? "Threads could not be loaded."
            : null,
      threadsLoading: threadsQuery.isPending,
      threadsRefreshing: threadsQuery.isFetching,
      updateThread,
    }),
    [
      createDraftThread,
      refreshThreads,
      replaceDraftWithBackendThread,
      selectThread,
      selectedThread,
      selectedThreadId,
      threads,
      threadsQuery.error,
      threadsQuery.isError,
      threadsQuery.isFetching,
      threadsQuery.isPending,
      updateThread,
    ],
  );

  return (
    <AssistantWorkspaceContext.Provider value={value}>
      {children}
    </AssistantWorkspaceContext.Provider>
  );
}

export function useAssistantWorkspace(): AssistantWorkspaceContextValue {
  const value = useContext(AssistantWorkspaceContext);
  if (!value) {
    throw new Error("useAssistantWorkspace must be used within AssistantWorkspaceProvider");
  }
  return value;
}
