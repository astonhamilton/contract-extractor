import { useEffect, useMemo, useState } from "react";
import AppShell, { type AppView } from "./AppShell";
import CorpusPage from "../features/corpus/pages/CorpusPage";
import AssistantPage from "../features/assistant/pages/AssistantPage";
import { corpusDocuments } from "../features/corpus/mock/documents";
import type { AssistantMessage, AssistantThread } from "../features/assistant/types";
import useStoredState from "../lib/useStoredState";
import {
  createAssistantThread,
  getAssistantThreads,
  postAssistantThreadMessage,
  suggestAssistantThreadTitle,
  threadFromDetailApi,
  threadSummaryFromApiItem,
  updateAssistantThreadTitle,
} from "../lib/api/assistant";

function isCorpusRoute(pathname: string, search: string): boolean {
  const params = new URLSearchParams(search);
  return (
    pathname.startsWith("/corpus") ||
    params.has("doc") ||
    params.has("tab") ||
    params.has("page")
  );
}

function nowTimestamp(): string {
  return new Date().toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}

function optimisticUserMessage(content: string): AssistantMessage {
  return {
    id: `local-user-${Date.now()}`,
    kind: "message",
    role: "user",
    title: "User",
    content,
    timestamp: nowTimestamp(),
  };
}

export default function App() {
  const [activeView, setActiveView] = useStoredState<AppView>(
    "ci.app.activeView",
    "assistant",
    { storage: "session" },
  );
  const [sidebarCollapsed, setSidebarCollapsed] = useStoredState(
    "ci.app.sidebarCollapsed",
    false,
  );
  const [draftThreads, setDraftThreads] = useStoredState<AssistantThread[]>(
    "ci.assistant.draftThreads",
    [],
    { storage: "session" },
  );
  const [selectedThreadId, setSelectedThreadId] = useStoredState(
    "ci.assistant.selectedThreadId",
    "",
    { storage: "session" },
  );
  const [backendThreads, setBackendThreads] = useState<AssistantThread[]>([]);
  const [threadsLoading, setThreadsLoading] = useState(true);
  const [threadsError, setThreadsError] = useState<string | null>(null);

  const threads = useMemo(
    () => [...draftThreads, ...backendThreads],
    [backendThreads, draftThreads],
  );

  const selectedThread =
    threads.find((thread) => thread.id === selectedThreadId) ?? null;

  useEffect(() => {
    function syncViewFromUrl(): void {
      if (isCorpusRoute(window.location.pathname, window.location.search)) {
        setActiveView("corpus");
      }
    }

    syncViewFromUrl();
    window.addEventListener("popstate", syncViewFromUrl);
    return () => {
      window.removeEventListener("popstate", syncViewFromUrl);
    };
  }, [setActiveView]);

  useEffect(() => {
    let cancelled = false;

    async function loadThreads() {
      setThreadsLoading(true);
      setThreadsError(null);
      try {
        const response = await getAssistantThreads();
        if (cancelled) {
          return;
        }
        setBackendThreads(response.items.map(threadSummaryFromApiItem));
      } catch {
        if (!cancelled) {
          setBackendThreads([]);
          setThreadsError("Could not load backend threads.");
        }
      } finally {
        if (!cancelled) {
          setThreadsLoading(false);
        }
      }
    }

    loadThreads();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    function handleWindowFocus() {
      void refreshThreads();
    }

    window.addEventListener("focus", handleWindowFocus);
    return () => {
      window.removeEventListener("focus", handleWindowFocus);
    };
  }, []);

  useEffect(() => {
    if (threads.length === 0) {
      setSelectedThreadId("");
      return;
    }

    if (selectedThreadId && !threads.some((thread) => thread.id === selectedThreadId)) {
      setSelectedThreadId("");
    }
  }, [selectedThreadId, setSelectedThreadId, threads]);

  function updateThreadLocal(
    threadId: string,
    updater: (thread: AssistantThread) => AssistantThread,
  ) {
    if (draftThreads.some((thread) => thread.id === threadId)) {
      setDraftThreads((current) =>
        current.map((thread) => (thread.id === threadId ? updater(thread) : thread)),
      );
      return;
    }

    setBackendThreads((current) =>
      current.map((thread) => (thread.id === threadId ? updater(thread) : thread)),
    );
  }

  function replaceDraftWithBackendThread(
    draftId: string,
    replacement: AssistantThread,
  ): void {
    setDraftThreads((current) => current.filter((thread) => thread.id !== draftId));
    setBackendThreads((current) => {
      const withoutExisting = current.filter(
        (thread) => thread.id !== replacement.id,
      );
      return [replacement, ...withoutExisting];
    });
    setSelectedThreadId(replacement.id);
  }

  async function refreshThreads(): Promise<void> {
    try {
      const response = await getAssistantThreads();
      setBackendThreads(response.items.map(threadSummaryFromApiItem));
      setThreadsError(null);
    } catch {
      setThreadsError("Could not refresh backend threads.");
    }
  }

  function handleSelectThread(threadId: string) {
    setSelectedThreadId(threadId);
    setActiveView("assistant");
  }

  function handleCreateThread() {
    const nextThread: AssistantThread = {
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
    setDraftThreads((current) => [nextThread, ...current]);
    setSelectedThreadId(nextThread.id);
    setActiveView("assistant");
  }

  async function handleSuggestThreadTitle(threadId: string): Promise<string> {
    const thread = threads.find((entry) => entry.id === threadId);
    if (!thread) {
      return "";
    }

    const digest = thread.messages
      .filter((message) => message.kind === "message" && message.role)
      .map((message) => `${message.role}: ${message.content.replace(/\s+/g, " ").trim()}`)
      .join("\n");

    if (!digest.trim()) {
      return "";
    }

    const response = await suggestAssistantThreadTitle(digest);
    return response.title.trim();
  }

  async function handleRenameThread(threadId: string, title: string): Promise<void> {
    const trimmed = title.trim();
    if (!trimmed) {
      return;
    }

    const thread = threads.find((entry) => entry.id === threadId);
    if (!thread) {
      return;
    }

    if (thread.isDraft || thread.backendThreadId === null) {
      updateThreadLocal(threadId, (current) => ({
        ...current,
        title: trimmed,
        updatedAt: "just now",
      }));
      return;
    }

    const updated = await updateAssistantThreadTitle(thread.backendThreadId, trimmed);
    updateThreadLocal(threadId, (current) => ({
      ...current,
      title: updated.title,
      updatedAt: "just now",
    }));
    void refreshThreads();
  }

  async function handleSendMessage(threadId: string, message: string): Promise<void> {
    const trimmed = message.trim();
    if (!trimmed) {
      return;
    }

    const thread = threads.find((entry) => entry.id === threadId);
    if (!thread) {
      return;
    }

    const userMessage = optimisticUserMessage(trimmed);

    updateThreadLocal(threadId, (current) => ({
      ...current,
      status: current.isDraft ? "retrieving" : "streaming",
      updatedAt: "just now",
      summary: trimmed,
      messages: [...current.messages, userMessage],
      itemsLoaded: true,
    }));

    if (thread.isDraft || thread.backendThreadId === null) {
      const titleSuggestionPromise = suggestAssistantThreadTitle(trimmed)
        .then((response) => response.title.trim())
        .catch(() => "");

      try {
        const created = await createAssistantThread(trimmed);
        const backendThread = threadFromDetailApi(created.thread, {
          ...thread,
          id: created.thread.thread_id,
          backendThreadId: created.thread.thread_id,
          title: created.thread.title,
          summary: trimmed,
          status: "streaming",
          updatedAt: "just now",
          messages: [userMessage],
          isDraft: false,
          itemsLoaded: false,
        });

        replaceDraftWithBackendThread(threadId, {
          ...backendThread,
          messages: [userMessage],
          status: "streaming",
          summary: trimmed,
          itemsLoaded: false,
        });

        const suggestedTitle = await titleSuggestionPromise;
        if (suggestedTitle) {
          const updated = await updateAssistantThreadTitle(
            created.thread.thread_id,
            suggestedTitle,
          );
          updateThreadLocal(created.thread.thread_id, (current) => ({
            ...current,
            title: updated.title,
            updatedAt: "just now",
          }));
        }

        void refreshThreads();
      } catch {
        updateThreadLocal(threadId, (current) => ({
          ...current,
          status: "error",
          summary: "Could not start this thread. Try sending again.",
        }));
      }
      return;
    }

    try {
      const posted = await postAssistantThreadMessage(thread.backendThreadId, trimmed);
      updateThreadLocal(threadId, (current) => ({
        ...current,
        ...threadFromDetailApi(posted.thread, current),
        summary: trimmed,
        status: "streaming",
      }));
      void refreshThreads();
    } catch {
      updateThreadLocal(threadId, (current) => ({
        ...current,
        status: "error",
      }));
    }
  }

  return (
    <AppShell
      activeView={activeView}
      onChangeView={setActiveView}
      sidebarCollapsed={sidebarCollapsed}
      onToggleSidebar={() => setSidebarCollapsed((value) => !value)}
      threads={threads}
      threadsLoading={threadsLoading}
      threadsError={threadsError}
      selectedThreadId={selectedThreadId}
      onSelectThread={handleSelectThread}
      onCreateThread={handleCreateThread}
      onRefreshThreads={() => {
        void refreshThreads();
      }}
      onSuggestThreadTitle={handleSuggestThreadTitle}
      onRenameThread={handleRenameThread}
    >
      {activeView === "corpus" ? (
        <CorpusPage documents={corpusDocuments} />
      ) : (
        <AssistantPage
          thread={selectedThread}
          onUpdateThread={updateThreadLocal}
          onSendMessage={handleSendMessage}
          onCreateThread={handleCreateThread}
        />
      )}
    </AppShell>
  );
}
