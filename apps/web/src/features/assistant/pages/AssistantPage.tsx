import type { AssistantThread } from "../types";
import ConversationPane from "../components/ConversationPane";

type AssistantPageProps = {
  thread: AssistantThread | null;
  onUpdateThread: (
    threadId: string,
    updater: (thread: AssistantThread) => AssistantThread,
  ) => void;
  onSendMessage: (threadId: string, message: string) => Promise<void>;
  onCreateThread: () => void;
};

export default function AssistantPage({
  thread,
  onUpdateThread,
  onSendMessage,
  onCreateThread,
}: AssistantPageProps) {
  if (!thread) {
    return (
      <section className="workspace-shell">
        <div className="assistant-layout">
          <section className="panel conversation-panel">
            <div className="assistant-empty-state">
              <div className="assistant-empty-glyph" aria-hidden="true">
                ◫
              </div>
              <p className="section-kicker">Assistant</p>
              <h3>Select a thread or start a new one</h3>
              <p>
                Choose a thread from the left to continue, or create a new thread to
                ask a question.
              </p>
              <button
                type="button"
                className="page-nav-button"
                onClick={onCreateThread}
              >
                Start new thread
              </button>
            </div>
          </section>
        </div>
      </section>
    );
  }

  return (
    <section className="workspace-shell">
      <div className="assistant-layout">
        <ConversationPane
          thread={thread}
          onUpdateThread={onUpdateThread}
          onSendMessage={onSendMessage}
        />
      </div>
    </section>
  );
}
