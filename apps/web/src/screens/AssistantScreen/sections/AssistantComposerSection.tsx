import type { FormEvent, KeyboardEvent } from "react";
import { SendHorizontal } from "lucide-react";
import { Button } from "@/ui/primitives/Button/Button";
import { Spinner } from "@/ui/primitives/Spinner/Spinner";
import styles from "./AssistantComposerSection.module.css";

type AssistantComposerSectionProps = {
  disabled: boolean;
  draft: string;
  isSending: boolean;
  onDraftChange: (draft: string) => void;
  onSendMessage: () => Promise<void>;
};

export function AssistantComposerSection({
  disabled,
  draft,
  isSending,
  onDraftChange,
  onSendMessage,
}: AssistantComposerSectionProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    void onSendMessage();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>): void {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }
    event.preventDefault();
    void onSendMessage();
  }

  return (
    <section className={styles.root} aria-label="Message composer">
      <form className={styles.form} onSubmit={handleSubmit}>
        <textarea
          className={styles.input}
          disabled={disabled}
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            disabled ? "Select or create a thread to ask a question." : "Ask a question..."
          }
          rows={1}
          value={draft}
        />
        <Button disabled={disabled || !draft.trim()} type="submit" variant="primary">
          {isSending ? <Spinner /> : <SendHorizontal size={16} aria-hidden="true" />}
          Send
        </Button>
      </form>
    </section>
  );
}

