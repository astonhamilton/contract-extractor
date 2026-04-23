import type { ReactNode } from "react";
import type { AssistantThread } from "../features/assistant/types";
import { useMemo, useState } from "react";

export type AppView = "corpus" | "assistant";

type AppShellProps = {
  activeView: AppView;
  onChangeView: (view: AppView) => void;
  sidebarCollapsed: boolean;
  onToggleSidebar: () => void;
  threads: AssistantThread[];
  threadsLoading: boolean;
  threadsError: string | null;
  selectedThreadId: string;
  onSelectThread: (threadId: string) => void;
  onCreateThread: () => void;
  onRefreshThreads: () => void;
  onSuggestThreadTitle: (threadId: string) => Promise<string>;
  onRenameThread: (threadId: string, title: string) => Promise<void>;
  children: ReactNode;
};

export default function AppShell({
  activeView,
  onChangeView,
  sidebarCollapsed,
  onToggleSidebar,
  threads,
  threadsLoading,
  threadsError,
  selectedThreadId,
  onSelectThread,
  onCreateThread,
  onRefreshThreads,
  onSuggestThreadTitle,
  onRenameThread,
  children,
}: AppShellProps) {
  const [renamingThreadId, setRenamingThreadId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [suggestedTitle, setSuggestedTitle] = useState("");
  const [suggestingTitle, setSuggestingTitle] = useState(false);

  const renamingThread = useMemo(
    () => threads.find((thread) => thread.id === renamingThreadId) ?? null,
    [renamingThreadId, threads],
  );

  function normalizedPreview(value: string): string {
    return value.replace(/\s+/g, " ").trim();
  }

  async function handleRenameSubmit(): Promise<void> {
    if (!renamingThreadId) {
      return;
    }
    const trimmed = renameValue.trim();
    if (!trimmed) {
      return;
    }
    await onRenameThread(renamingThreadId, trimmed);
    setRenamingThreadId(null);
    setRenameValue("");
    setSuggestedTitle("");
  }

  async function handleSuggestTitle(): Promise<void> {
    if (!renamingThreadId) {
      return;
    }
    setSuggestingTitle(true);
    try {
      const suggestion = await onSuggestThreadTitle(renamingThreadId);
      setSuggestedTitle(suggestion);
    } finally {
      setSuggestingTitle(false);
    }
  }

  return (
    <div className="app-frame">
      <aside
        className={sidebarCollapsed ? "app-sidebar app-sidebar-collapsed" : "app-sidebar"}
      >
        <div className="sidebar-top">
          <div className="sidebar-title-row">
            <button
              type="button"
              className="icon-button"
              onClick={onToggleSidebar}
              aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              <span className="burger-lines" />
            </button>
            {!sidebarCollapsed ? (
              <span className="sidebar-app-title">Contract Intelligence</span>
            ) : null}
          </div>
        </div>

        <div className="sidebar-primary">
          {!sidebarCollapsed ? <p className="section-kicker">Browse</p> : null}
          <button
            type="button"
            className={
              activeView === "corpus"
                ? "nav-card nav-card-active nav-card-compact"
                : "nav-card nav-card-compact"
            }
            onClick={() => onChangeView("corpus")}
            title="Browse corpus"
          >
            <span className="nav-icon" aria-hidden="true">
              ◫
            </span>
            {!sidebarCollapsed ? (
              <span className="nav-label">Browse corpus</span>
            ) : null}
          </button>
        </div>

        <div className="sidebar-thread-section">
          <div className="sidebar-thread-header">
            {!sidebarCollapsed ? (
              <>
                <span className="section-kicker">Threads</span>
                <div className="sidebar-thread-actions">
                  <button
                    type="button"
                    className="icon-button icon-button-soft"
                    onClick={onRefreshThreads}
                    aria-label="Refresh threads"
                    title="Refresh threads"
                  >
                    <span className="refresh-glyph" aria-hidden="true">
                      ↺
                    </span>
                  </button>
                  <button
                    type="button"
                    className="icon-button icon-button-soft"
                    onClick={onCreateThread}
                    aria-label="Create new thread"
                    title="Create new thread"
                  >
                    +
                  </button>
                </div>
              </>
            ) : (
              <div className="sidebar-thread-actions">
                <button
                  type="button"
                  className="icon-button icon-button-soft"
                  onClick={onRefreshThreads}
                  aria-label="Refresh threads"
                  title="Refresh threads"
                >
                  <span className="refresh-glyph" aria-hidden="true">
                    ↺
                  </span>
                </button>
                <button
                  type="button"
                  className="icon-button icon-button-soft"
                  onClick={onCreateThread}
                  aria-label="Create new thread"
                  title="Create new thread"
                >
                  +
                </button>
              </div>
            )}
          </div>

          <div className="sidebar-thread-list">
            {threadsLoading ? (
              <div className="sidebar-thread-feedback" role="status">
                <span className="section-kicker">Loading</span>
                {!sidebarCollapsed ? (
                  <p>Fetching your threads…</p>
                ) : (
                  <span className="collapsed-thread-glyph" aria-hidden="true">
                    ◦
                  </span>
                )}
              </div>
            ) : threadsError ? (
              <div className="sidebar-thread-feedback sidebar-thread-feedback-error">
                <span className="section-kicker">Unavailable</span>
                {!sidebarCollapsed ? (
                  <p>{threadsError}</p>
                ) : (
                  <span className="collapsed-thread-glyph" aria-hidden="true">
                    !
                  </span>
                )}
              </div>
            ) : threads.length === 0 ? (
              <div className="sidebar-thread-feedback">
                <span className="section-kicker">No threads</span>
                {!sidebarCollapsed ? (
                  <p>Create a new thread to start asking questions.</p>
                ) : (
                  <span className="collapsed-thread-glyph" aria-hidden="true">
                    ◦
                  </span>
                )}
              </div>
            ) : (
              threads.map((thread) => (
                <button
                  key={thread.id}
                  type="button"
                  className={
                    thread.id === selectedThreadId && activeView === "assistant"
                      ? thread.isDraft
                        ? "sidebar-thread-row sidebar-thread-row-active sidebar-thread-row-draft"
                        : "sidebar-thread-row sidebar-thread-row-active"
                      : thread.isDraft
                        ? "sidebar-thread-row sidebar-thread-row-draft"
                        : "sidebar-thread-row"
                  }
                  onClick={() => onSelectThread(thread.id)}
                  title={thread.title}
                >
                  <div className="sidebar-thread-row-topline">
                    {!sidebarCollapsed ? (
                      <>
                        <strong>{thread.title}</strong>
                        <span className="sidebar-thread-updated">{thread.updatedAt}</span>
                      </>
                    ) : null}
                  </div>
                  {!sidebarCollapsed ? (
                    <div className="sidebar-thread-row-copy">
                      <div className="sidebar-thread-row-copyline">
                        <p>{normalizedPreview(thread.summary)}</p>
                        <button
                          type="button"
                          className="conversation-event-button sidebar-thread-edit-button"
                          aria-label={`Rename ${thread.title}`}
                          onClick={(event) => {
                            event.stopPropagation();
                            setRenamingThreadId(thread.id);
                            setRenameValue(thread.title);
                            setSuggestedTitle("");
                          }}
                        >
                          ✎
                        </button>
                      </div>
                    </div>
                  ) : (
                    <span className="collapsed-thread-glyph" aria-hidden="true">
                      ◦
                    </span>
                  )}
                </button>
              ))
            )}
          </div>
        </div>
      </aside>

      {renamingThread ? (
        <div
          className="dialog-backdrop"
          role="presentation"
          onClick={() => {
            setRenamingThreadId(null);
            setRenameValue("");
            setSuggestedTitle("");
          }}
        >
          <div
            className="dialog-shell"
            role="dialog"
            aria-modal="true"
            aria-label="Rename thread"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="dialog-header">
              <div>
                <p className="section-kicker">Thread</p>
                <h3>Rename thread</h3>
              </div>
              <button
                type="button"
                className="dialog-close"
                aria-label="Close rename dialog"
                onClick={() => {
                  setRenamingThreadId(null);
                  setRenameValue("");
                  setSuggestedTitle("");
                }}
              >
                ×
              </button>
            </div>
            <p className="dialog-meta">Update how this thread appears in the sidebar.</p>
            <div className="dialog-form">
              <input
                type="text"
                className="composer-input"
                value={renameValue}
                onChange={(event) => setRenameValue(event.target.value)}
                placeholder="Thread title"
                autoFocus
              />
              {suggestedTitle ? (
                <button
                  type="button"
                  className="dialog-suggestion"
                  onClick={() => setRenameValue(suggestedTitle)}
                >
                  <span className="dialog-suggestion-label">Suggested title</span>
                  <span>{suggestedTitle}</span>
                </button>
              ) : null}
              <div className="dialog-actions">
                <button
                  type="button"
                  className="secondary-action"
                  onClick={() => {
                    void handleSuggestTitle();
                  }}
                  disabled={suggestingTitle}
                >
                  {suggestingTitle ? "Suggesting..." : "Suggest title"}
                </button>
                <button
                  type="button"
                  className="secondary-action"
                  onClick={() => {
                    setRenamingThreadId(null);
                    setRenameValue("");
                    setSuggestedTitle("");
                  }}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="primary-action"
                  onClick={() => {
                    void handleRenameSubmit();
                  }}
                  disabled={!renameValue.trim()}
                >
                  Save
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      <main className="app-main">{children}</main>
    </div>
  );
}
