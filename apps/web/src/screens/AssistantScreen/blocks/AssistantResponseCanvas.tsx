import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Braces } from "lucide-react";
import type { AssistantMessage } from "@/screens/AssistantScreen/AssistantScreen.types";
import { IconButton } from "@/ui/primitives/IconButton/IconButton";
import styles from "./AssistantResponseCanvas.module.css";

type AssistantResponseCanvasProps = {
  message: AssistantMessage;
  onOpenDebug: (messageId: string) => void;
};

export function AssistantResponseCanvas({
  message,
  onOpenDebug,
}: AssistantResponseCanvasProps) {
  return (
    <article className={styles.root}>
      <div className={styles.topline}>
        <span>Assistant</span>
        <div className={styles.actions}>
          <span>{message.timestamp}</span>
          <IconButton
            aria-label="Open assistant message debug JSON"
            className={styles.debug}
            onClick={() => onOpenDebug(message.id)}
            tooltip="Debug JSON"
          >
            <Braces size={14} aria-hidden="true" />
          </IconButton>
        </div>
      </div>
      <div className={styles.markdown}>
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
    </article>
  );
}

