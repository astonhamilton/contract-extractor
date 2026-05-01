import { Braces } from "lucide-react";
import type { AssistantMessage } from "@/screens/AssistantScreen/AssistantScreen.types";
import { IconButton } from "@/ui/primitives/IconButton/IconButton";
import styles from "./AssistantUserMessageBubble.module.css";

type AssistantUserMessageBubbleProps = {
  message: AssistantMessage;
  onOpenDebug: (messageId: string) => void;
};

export function AssistantUserMessageBubble({
  message,
  onOpenDebug,
}: AssistantUserMessageBubbleProps) {
  return (
    <article className={styles.root}>
      <div className={styles.bubble}>
        <p>{message.content}</p>
        <div className={styles.meta}>
          <span>{message.timestamp}</span>
          <IconButton
            aria-label="Open user message debug JSON"
            className={styles.debug}
            onClick={() => onOpenDebug(message.id)}
            tooltip="Debug JSON"
          >
            <Braces size={14} aria-hidden="true" />
          </IconButton>
        </div>
      </div>
    </article>
  );
}

