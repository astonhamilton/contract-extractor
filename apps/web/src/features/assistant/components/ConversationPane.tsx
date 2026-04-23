import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { AssistantMessage, AssistantThread } from "../types";
import useStoredState from "../../../lib/useStoredState";
import {
  getAssistantThreadItems,
  messageFromApiItem,
  threadFromDetailApi,
  type AssistantThreadItemsApiResponse,
} from "../../../lib/api/assistant";

type ConversationPaneProps = {
  thread: AssistantThread;
  onUpdateThread: (
    threadId: string,
    updater: (thread: AssistantThread) => AssistantThread,
  ) => void;
  onSendMessage: (threadId: string, message: string) => Promise<void>;
};

type RefreshState = "ready" | "working" | "error";

function eventLabel(message: AssistantMessage): string {
  if (message.kind === "reasoning") {
    return "Reasoning";
  }
  if (message.kind === "tool_call") {
    return "Tool call";
  }
  if (message.kind === "tool_result") {
    return "Tool result";
  }
  if (message.kind === "hosted_tool_event") {
    return "Hosted tool";
  }
  return message.title;
}

function isHostedWebSearchEvent(message: AssistantMessage): boolean {
  return (
    message.kind === "hosted_tool_event" &&
    (message.rawItem?.record?.name === "web_search_call" ||
      message.rawItem?.record?.provider_item_type === "web_search_call")
  );
}

function isImageGenerationEvent(message: AssistantMessage): boolean {
  return (
    message.kind === "hosted_tool_event" &&
    (message.rawItem?.record?.name === "image_generation_call" ||
      message.rawItem?.record?.provider_item_type === "image_generation_call")
  );
}

function imageGenerationPayload(message: AssistantMessage): Record<string, unknown> | null {
  const payload = message.rawItem?.record?.provider_payload;
  return payload && typeof payload === "object" ? payload : null;
}

function imageGenerationDataUrl(message: AssistantMessage): string | null {
  const payload = imageGenerationPayload(message);
  const result = payload?.result;
  const format = payload?.output_format;
  if (typeof result !== "string" || !result.trim()) {
    return null;
  }
  const mime = typeof format === "string" && format ? `image/${format}` : "image/png";
  return `data:${mime};base64,${result}`;
}

function imageGenerationMeta(message: AssistantMessage): string {
  const payload = imageGenerationPayload(message);
  const parts = [
    typeof payload?.size === "string" ? payload.size : "",
    typeof payload?.output_format === "string" ? payload.output_format : "",
    typeof payload?.quality === "string" ? payload.quality : "",
  ].filter(Boolean);
  return parts.join(" · ");
}

function formatToolArgumentValue(value: unknown): string {
  if (value == null) {
    return "null";
  }
  if (typeof value === "string") {
    return value;
  }
  if (
    typeof value === "number" ||
    typeof value === "boolean" ||
    typeof value === "bigint"
  ) {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value.map((item) => formatToolArgumentValue(item)).join(",");
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function toolCallArgumentSummary(message: AssistantMessage): string {
  const rawArguments = message.rawItem?.record?.arguments;
  if (!rawArguments || typeof rawArguments !== "object") {
    return "";
  }
  const entries = Object.entries(rawArguments as Record<string, unknown>);
  if (entries.length === 0) {
    return "";
  }
  return entries
    .map(([key, value]) => `${key}=${formatToolArgumentValue(value)}`)
    .join(", ");
}

function hostedWebSearchQuery(message: AssistantMessage): string {
  const action = message.rawItem?.record?.provider_payload?.action;
  if (action && typeof action === "object") {
    const query = (action as Record<string, unknown>).query;
    if (typeof query === "string" && query.trim()) {
      return query.trim();
    }
  }
  return message.content;
}

function hostedWebSearchResultCount(message: AssistantMessage): number {
  const results = message.rawItem?.record?.provider_payload?.results;
  return Array.isArray(results) ? results.length : 0;
}

function hostedWebSearchDomainSummary(message: AssistantMessage): string {
  const action = message.rawItem?.record?.provider_payload?.action;
  const sources =
    action && typeof action === "object"
      ? (action as Record<string, unknown>).sources
      : null;
  if (!Array.isArray(sources)) {
    return "";
  }

  const domains = new Set<string>();
  for (const source of sources) {
    if (!source || typeof source !== "object") {
      continue;
    }
    const url = (source as Record<string, unknown>).url;
    if (typeof url !== "string") {
      continue;
    }
    try {
      const hostname = new URL(url).hostname.replace(/^www\./, "");
      if (hostname) {
        domains.add(hostname);
      }
    } catch {
      continue;
    }
  }

  const orderedDomains = [...domains];
  if (orderedDomains.length === 0) {
    return "";
  }
  const visible = orderedDomains.slice(0, 3);
  const remainder = orderedDomains.length - visible.length;
  return remainder > 0
    ? `${visible.join(", ")} +${remainder}`
    : visible.join(", ");
}

function isLastTurnInProgress(
  lastTurn: AssistantThreadItemsApiResponse["last_turn"] | null,
): boolean {
  if (!lastTurn) {
    return false;
  }
  return (
    lastTurn.status === "queued" ||
    lastTurn.status === "running" ||
    lastTurn.phase === "queued" ||
    lastTurn.phase === "running" ||
    lastTurn.phase === "working"
  );
}

function isActiveTurnInProgress(
  activeTurn: AssistantThreadItemsApiResponse["active_turn"] | null,
): boolean {
  return activeTurn != null;
}

function refreshLabel(state: RefreshState, isActiveTurn: boolean): string {
  if (state === "error") {
    return "Refresh issue";
  }
  if (isActiveTurn) {
    return "Working";
  }
  return "Up to date";
}

function sortedMessages(messages: AssistantMessage[]): AssistantMessage[] {
  return [...messages].sort((left, right) => {
    const leftSeq = left.seq ?? Number.MAX_SAFE_INTEGER;
    const rightSeq = right.seq ?? Number.MAX_SAFE_INTEGER;
    if (leftSeq !== rightSeq) {
      return leftSeq - rightSeq;
    }
    return left.timestamp.localeCompare(right.timestamp);
  });
}

function transcriptFilename(thread: AssistantThread): string {
  const slug = thread.title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
  return `${slug || "thread"}-transcript.md`;
}

function eventMarkdown(message: AssistantMessage): string {
  if (message.kind === "tool_call") {
    const toolName =
      (message.rawItem?.record?.name as string | undefined) ?? message.title;
    const rawArguments = message.rawItem?.record?.arguments;
    const args =
      rawArguments && Object.keys(rawArguments).length > 0
        ? `\narguments: \`${JSON.stringify(rawArguments)}\``
        : "";
    return `- Tool call: **${toolName}**${args}`;
  }

  if (isHostedWebSearchEvent(message)) {
    const query = hostedWebSearchQuery(message);
    const count = hostedWebSearchResultCount(message);
    const domains = hostedWebSearchDomainSummary(message);
    return `- Web search: **${query}**${count ? `\nresults: ${count}` : ""}${
      domains ? `\nsources: ${domains}` : ""
    }`;
  }

  if (message.kind === "reasoning") {
    return `- Reasoning: ${message.content}`;
  }

  return `- ${eventLabel(message)}: ${message.content}`;
}

function transcriptMarkdown(
  thread: AssistantThread,
  messages: AssistantMessage[],
  lastTurn: AssistantThreadItemsApiResponse["last_turn"] | null,
): string {
  const header = [
    `# ${thread.title}`,
    "",
    `- Thread ID: ${thread.backendThreadId ?? thread.id}`,
    lastTurn ? `- Last turn ID: ${lastTurn.turn_id}` : "",
    lastTurn ? `- Last turn status: ${lastTurn.status}` : "",
    `- Updated: ${thread.updatedAt}`,
    "",
    "---",
    "",
  ].filter(Boolean);

  const body = messages.flatMap((message) => {
    if (message.kind === "message") {
      const role = message.role === "assistant" ? "Assistant" : "User";
      return [`## ${role} · ${message.timestamp}`, "", message.content, ""];
    }
    return [`## Event · ${message.timestamp}`, "", eventMarkdown(message), ""];
  });

  return [...header, ...body].join("\n");
}

export default function ConversationPane({
  thread,
  onUpdateThread,
  onSendMessage,
}: ConversationPaneProps) {
  const [activeEventId, setActiveEventId] = useState<string | null>(null);
  const [activeDebugId, setActiveDebugId] = useState<string | null>(null);
  const [activeImageId, setActiveImageId] = useState<string | null>(null);
  const [refreshState, setRefreshState] = useState<RefreshState>("ready");
  const [activeTurn, setActiveTurn] =
    useState<AssistantThreadItemsApiResponse["active_turn"] | null>(null);
  const [lastTurn, setLastTurn] =
    useState<AssistantThreadItemsApiResponse["last_turn"] | null>(null);
  const [draftsByThread, setDraftsByThread] = useStoredState<
    Record<string, string>
  >("ci.assistant.drafts", {}, { storage: "session" });
  const stackRef = useRef<HTMLDivElement | null>(null);
  const draft = draftsByThread[thread.id] ?? "";

  const activeEvent = useMemo(
    () => thread.messages.find((message) => message.id === activeEventId) ?? null,
    [activeEventId, thread.messages],
  );
  const activeDebugMessage = useMemo(
    () => thread.messages.find((message) => message.id === activeDebugId) ?? null,
    [activeDebugId, thread.messages],
  );
  const activeImageMessage = useMemo(
    () => thread.messages.find((message) => message.id === activeImageId) ?? null,
    [activeImageId, thread.messages],
  );
  useEffect(() => {
    const stack = stackRef.current;
    if (!stack) {
      return;
    }
    stack.scrollTop = stack.scrollHeight;
  }, [thread.messages]);

  useEffect(() => {
    if (!thread.backendThreadId) {
      setRefreshState("ready");
      setActiveTurn(null);
      setLastTurn(null);
      return;
    }
  }, [thread.backendThreadId]);

  const refreshThread = useCallback(async (): Promise<void> => {
    if (!thread.backendThreadId) {
      return;
    }
    try {
      setRefreshState((current) =>
        isActiveTurnInProgress(activeTurn) || thread.status === "streaming" || !thread.itemsLoaded
          ? "working"
          : current,
      );
      const items = await getAssistantThreadItems(thread.backendThreadId);
      setActiveTurn(items.active_turn);
      setLastTurn(items.last_turn);
      setRefreshState("ready");
      onUpdateThread(thread.id, (current) => ({
        ...threadFromDetailApi(items.thread, current),
        summary: current.summary,
        messages: sortedMessages(items.items.map(messageFromApiItem)),
        itemsLoaded: true,
      }));
    } catch {
      setRefreshState("error");
      onUpdateThread(thread.id, (current) => ({
        ...current,
        status: current.status === "draft" ? "draft" : "error",
      }));
    }
  }, [activeTurn, onUpdateThread, thread.backendThreadId, thread.id, thread.itemsLoaded, thread.status]);

  useEffect(() => {
    if (!thread.backendThreadId || thread.itemsLoaded) {
      return;
    }
    void refreshThread();
  }, [refreshThread, thread.backendThreadId, thread.itemsLoaded]);

  useEffect(() => {
    if (!thread.backendThreadId) {
      return;
    }
    const intervalMs = isActiveTurnInProgress(activeTurn) || thread.status === "streaming" ? 1000 : 30000;
    const timer = window.setInterval(() => {
      void refreshThread();
    }, intervalMs);
    return () => {
      window.clearInterval(timer);
    };
  }, [activeTurn, refreshThread, thread.backendThreadId, thread.status]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed) {
      return;
    }

    setDraftsByThread((current) => ({
      ...current,
      [thread.id]: "",
    }));
    setRefreshState("working");
    await onSendMessage(thread.id, trimmed);
  }

  function handleExportTranscript(): void {
    const markdown = transcriptMarkdown(thread, thread.messages, lastTurn);
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = window.document.createElement("a");
    anchor.href = url;
    anchor.download = transcriptFilename(thread);
    window.document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  }

  return (
    <section className="panel conversation-panel">
      <div className="conversation-header">
        <div>
          <p className="section-kicker">Thread</p>
          <h2 className="conversation-title">{thread.title}</h2>
        </div>
        <div className="conversation-header-meta">
          {thread.backendThreadId ? (
            <div className="conversation-header-actions">
              <button
                type="button"
                className="icon-button icon-button-soft"
                onClick={handleExportTranscript}
                aria-label="Export transcript as markdown"
                title="Export transcript as markdown"
              >
                <span className="refresh-glyph" aria-hidden="true">
                  ↓
                </span>
              </button>
              <button
                type="button"
                className="icon-button icon-button-soft"
                onClick={() => {
                  void refreshThread();
                }}
                aria-label="Refresh thread"
                title="Refresh thread"
              >
                <span className="refresh-glyph" aria-hidden="true">
                  ↺
                </span>
              </button>
              <div
                className={
                  refreshState === "error"
                    ? "stream-indicator stream-indicator-reconnecting"
                    : isActiveTurnInProgress(activeTurn)
                      ? "stream-indicator stream-indicator-working"
                      : "stream-indicator stream-indicator-connected"
                }
              >
              <span className="stream-bulb" />
              <span>{refreshLabel(refreshState, isActiveTurnInProgress(activeTurn))}</span>
              </div>
            </div>
          ) : null}
          <p className="conversation-updated">Updated {thread.updatedAt}</p>
        </div>
      </div>

      <div ref={stackRef} className="conversation-stack">
        {thread.messages.length === 0 ? (
          <div className="conversation-empty-state">
            <p className="conversation-empty-title">New thread</p>
            <p>Send the first message to create this thread in the backend.</p>
          </div>
        ) : null}

        {thread.messages.map((message) => {
          if (message.kind === "tool_result") {
            return null;
          }

          if (message.kind !== "message") {
            const isLocalToolCall =
              message.kind === "tool_call" &&
              message.rawItem?.record?.provider_item_type === "function_call";
            const isWebSearch = isHostedWebSearchEvent(message);
            const toolName =
              (message.rawItem?.record?.name as string | undefined) ??
              message.title;
            const toolArguments = isLocalToolCall
              ? toolCallArgumentSummary(message)
              : "";
            const searchQuery = isWebSearch ? hostedWebSearchQuery(message) : "";
            const searchResultCount = isWebSearch
              ? hostedWebSearchResultCount(message)
              : 0;
            const searchDomains = isWebSearch
              ? hostedWebSearchDomainSummary(message)
              : "";
            const isImageGeneration = isImageGenerationEvent(message);
            const imageDataUrl = isImageGeneration
              ? imageGenerationDataUrl(message)
              : null;
            const imageMeta = isImageGeneration ? imageGenerationMeta(message) : "";
            const imagePrompt = isImageGeneration
              ? imageGenerationPayload(message)?.revised_prompt
              : "";
            return (
              <article key={message.id} className="conversation-event-row">
                <div className="conversation-event-copy">
                  {isImageGeneration ? (
                    <div className="conversation-image-artifact">
                      <span className="conversation-event-label">Generated image</span>
                      {imageDataUrl ? (
                        <button
                          type="button"
                          className="conversation-image-button"
                          onClick={() => setActiveImageId(message.id)}
                          aria-label="Open generated image"
                        >
                          <img
                            className="conversation-image-thumb"
                            src={imageDataUrl}
                            alt="Generated image artifact"
                          />
                        </button>
                      ) : (
                        <div className="conversation-image-thumb conversation-image-thumb-empty">
                          Image unavailable
                        </div>
                      )}
                      {imageMeta ? (
                        <p className="conversation-event-args">{imageMeta}</p>
                      ) : null}
                      {typeof imagePrompt === "string" && imagePrompt.trim() ? (
                        <p className="conversation-event-args" title={imagePrompt}>
                          {imagePrompt}
                        </p>
                      ) : null}
                    </div>
                  ) : isLocalToolCall ? (
                    <>
                      <span className="conversation-event-label">Tool call</span>
                      <p className="conversation-event-title">{toolName}</p>
                      {toolArguments ? (
                        <p
                          className="conversation-event-args"
                          title={toolArguments}
                        >
                          {toolArguments}
                        </p>
                      ) : null}
                    </>
                  ) : isWebSearch ? (
                    <>
                      <span className="conversation-event-label">Web search</span>
                      <p className="conversation-event-title">{searchQuery}</p>
                      <p className="conversation-event-args">
                        {searchResultCount > 0
                          ? `${searchResultCount} results`
                          : "Search completed"}
                        {searchDomains ? ` · ${searchDomains}` : ""}
                      </p>
                    </>
                  ) : (
                    <>
                      <span className="conversation-event-label">
                        {eventLabel(message)}
                      </span>
                      <p>{message.content}</p>
                    </>
                  )}
                </div>
                <button
                  type="button"
                  className="conversation-event-button"
                  aria-label={`Open ${eventLabel(message)} details`}
                  onClick={() => setActiveEventId(message.id)}
                >
                  i
                </button>
                <button
                  type="button"
                  className="conversation-event-button"
                  aria-label={`Open ${eventLabel(message)} debug JSON`}
                  onClick={() => setActiveDebugId(message.id)}
                >
                  {"{}"}
                </button>
              </article>
            );
          }

          return (
            <article
              key={message.id}
              className={
                message.role === "user"
                  ? "message-bubble message-user"
                  : "message-bubble message-assistant"
              }
            >
              <div className="message-topline">
                <strong>{message.role ?? message.title}</strong>
                <div className="message-topline-actions">
                  <span>{message.timestamp}</span>
                  <button
                    type="button"
                    className="message-debug-button"
                    aria-label={`Open ${message.role ?? message.title} debug JSON`}
                    onClick={() => setActiveDebugId(message.id)}
                  >
                    {"{}"}
                  </button>
                </div>
              </div>
              {message.role === "assistant" ? (
                <div className="message-markdown">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      a: ({ ...props }) => (
                        <a {...props} target="_blank" rel="noreferrer" />
                      ),
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>
              ) : (
                <p>{message.content}</p>
              )}
            </article>
          );
        })}

        {isActiveTurnInProgress(activeTurn) ? (
          <div className="conversation-thinking-row" aria-live="polite">
            <div className="conversation-thinking-spinner" aria-hidden="true" />
            <span>Thinking…</span>
          </div>
        ) : null}
      </div>

      <form className="composer-shell" onSubmit={handleSubmit}>
        <div className="composer-copy">
          <input
            type="text"
            className="composer-input"
            value={draft}
            placeholder="Ask a follow-up..."
            onChange={(event) =>
              setDraftsByThread((current) => ({
                ...current,
                [thread.id]: event.target.value,
              }))
            }
          />
          <p className="composer-meta">
            Thread ID · {thread.backendThreadId ?? thread.id}
            {activeTurn
              ? ` · Active turn · ${activeTurn.turn_id} · ${activeTurn.status}`
              : lastTurn
                ? ` · No active turn · Last turn · ${lastTurn.turn_id} · ${lastTurn.status}`
                : " · No active turn"}
          </p>
        </div>
        <button type="submit" className="primary-action" disabled={!draft.trim()}>
          Send
        </button>
      </form>

      {activeEvent ? (
        <div
          className="dialog-backdrop"
          role="presentation"
          onClick={() => setActiveEventId(null)}
        >
          <div
            className="dialog-shell"
            role="dialog"
            aria-modal="true"
            aria-label={activeEvent.detailTitle ?? eventLabel(activeEvent)}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="dialog-header">
              <div>
                <p className="section-kicker">{eventLabel(activeEvent)}</p>
                <h3>{activeEvent.detailTitle ?? eventLabel(activeEvent)}</h3>
              </div>
              <button
                type="button"
                className="dialog-close"
                aria-label="Close details"
                onClick={() => setActiveEventId(null)}
              >
                ×
              </button>
            </div>
            <p className="dialog-meta">{activeEvent.timestamp}</p>
            {isImageGenerationEvent(activeEvent) ? (
              <div className="dialog-body">
                {imageGenerationDataUrl(activeEvent) ? (
                  <img
                    className="dialog-image"
                    src={imageGenerationDataUrl(activeEvent) ?? undefined}
                    alt="Generated image"
                  />
                ) : null}
                {imageGenerationMeta(activeEvent) ? (
                  <p className="dialog-meta">{imageGenerationMeta(activeEvent)}</p>
                ) : null}
                {typeof imageGenerationPayload(activeEvent)?.revised_prompt === "string" ? (
                  <pre className="dialog-pre">
                    {String(imageGenerationPayload(activeEvent)?.revised_prompt)}
                  </pre>
                ) : null}
              </div>
            ) : (
              <pre className="dialog-pre">
                {activeEvent.detailBody ?? activeEvent.content}
              </pre>
            )}
          </div>
        </div>
      ) : null}

      {activeDebugMessage ? (
        <div
          className="dialog-backdrop"
          role="presentation"
          onClick={() => setActiveDebugId(null)}
        >
          <div
            className="dialog-shell"
            role="dialog"
            aria-modal="true"
            aria-label="Raw item JSON"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="dialog-header">
              <div>
                <p className="section-kicker">Debug</p>
                <h3>Raw item JSON</h3>
              </div>
              <button
                type="button"
                className="dialog-close"
                aria-label="Close debug JSON"
                onClick={() => setActiveDebugId(null)}
              >
                ×
              </button>
            </div>
            <p className="dialog-meta">{activeDebugMessage.timestamp}</p>
            <pre className="dialog-pre">
              {activeDebugMessage.rawJson ??
                JSON.stringify(activeDebugMessage, null, 2)}
            </pre>
          </div>
        </div>
      ) : null}

      {activeImageMessage && imageGenerationDataUrl(activeImageMessage) ? (
        <div
          className="dialog-backdrop"
          role="presentation"
          onClick={() => setActiveImageId(null)}
        >
          <div
            className="dialog-shell dialog-shell-wide"
            role="dialog"
            aria-modal="true"
            aria-label="Generated image"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="dialog-header">
              <div>
                <p className="section-kicker">Generated image</p>
                <h3>{activeImageMessage.detailTitle ?? activeImageMessage.title}</h3>
              </div>
              <button
                type="button"
                className="dialog-close"
                aria-label="Close image preview"
                onClick={() => setActiveImageId(null)}
              >
                ×
              </button>
            </div>
            <p className="dialog-meta">{activeImageMessage.timestamp}</p>
            <div className="dialog-body">
              <img
                className="dialog-image"
                src={imageGenerationDataUrl(activeImageMessage) ?? undefined}
                alt="Generated image"
              />
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
