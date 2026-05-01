import { useEffect, useRef } from "react";
import { AssistantEventRow } from "@/screens/AssistantScreen/blocks/AssistantEventRow";
import { AssistantResponseCanvas } from "@/screens/AssistantScreen/blocks/AssistantResponseCanvas";
import { AssistantUserMessageBubble } from "@/screens/AssistantScreen/blocks/AssistantUserMessageBubble";
import type { AssistantMessage } from "@/screens/AssistantScreen/AssistantScreen.types";
import { Button } from "@/ui/primitives/Button/Button";
import { EmptyState } from "@/ui/patterns/EmptyState/EmptyState";
import { SkeletonStack } from "@/ui/patterns/SkeletonStack/SkeletonStack";
import { Spinner } from "@/ui/primitives/Spinner/Spinner";
import { StatusBanner } from "@/ui/patterns/StatusBanner/StatusBanner";
import styles from "./AssistantTranscriptSection.module.css";

type AssistantTranscriptSectionProps = {
  error: string | null;
  isWorking: boolean;
  messages: AssistantMessage[];
  onCreateThread: () => void;
  onOpenDebug: (messageId: string) => void;
  onOpenEvent: (messageId: string) => void;
  onOpenImage: (messageId: string) => void;
  status: "empty" | "loading" | "error" | "ready";
};

export function AssistantTranscriptSection({
  error,
  isWorking,
  messages,
  onCreateThread,
  onOpenDebug,
  onOpenEvent,
  onOpenImage,
  status,
}: AssistantTranscriptSectionProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const node = scrollRef.current;
    if (!node) {
      return;
    }
    node.scrollTop = node.scrollHeight;
  }, [messages.length, isWorking]);

  return (
    <section className={styles.root} aria-label="Assistant transcript">
      <div ref={scrollRef} className={styles.scroller}>
        {status === "empty" ? (
          <EmptyState
            actions={
              <Button onClick={onCreateThread} variant="primary">
                Start a thread
              </Button>
            }
            eyebrow="Assistant"
            title="Select a thread or start a new one"
          >
            <p>Use Assistant to ask focused questions and inspect the work behind each answer.</p>
          </EmptyState>
        ) : null}

        {status === "loading" ? <SkeletonStack rows={5} /> : null}

        {status === "error" ? (
          <StatusBanner tone="danger">{error ?? "Thread could not be loaded."}</StatusBanner>
        ) : null}

        {status === "ready" && messages.length === 0 ? (
          <EmptyState eyebrow="Thread" title="New thread">
            <p>Send the first message to create this thread.</p>
          </EmptyState>
        ) : null}

        {status === "ready"
          ? messages.map((message) => {
              if (message.kind === "tool_result") {
                return null;
              }
              if (message.kind !== "message") {
                return (
                  <AssistantEventRow
                    key={message.id}
                    message={message}
                    onOpenDebug={onOpenDebug}
                    onOpenDetail={onOpenEvent}
                    onOpenImage={onOpenImage}
                  />
                );
              }
              if (message.role === "user") {
                return (
                  <AssistantUserMessageBubble
                    key={message.id}
                    message={message}
                    onOpenDebug={onOpenDebug}
                  />
                );
              }
              return (
                <AssistantResponseCanvas
                  key={message.id}
                  message={message}
                  onOpenDebug={onOpenDebug}
                />
              );
            })
          : null}

        {isWorking ? (
          <div className={styles.working} aria-live="polite">
            <Spinner />
            <span>Assistant is working</span>
          </div>
        ) : null}
      </div>
    </section>
  );
}

