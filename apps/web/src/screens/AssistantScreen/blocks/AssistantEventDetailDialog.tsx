import { X } from "lucide-react";
import {
  eventLabel,
  imageGenerationDataUrl,
  imageGenerationPayload,
  isImageGenerationEvent,
} from "@/screens/AssistantScreen/AssistantScreen.helpers";
import type { AssistantMessage } from "@/screens/AssistantScreen/AssistantScreen.types";
import { Dialog, DialogClose } from "@/ui/primitives/Dialog/Dialog";
import { DialogFrame } from "@/ui/patterns/DialogFrame/DialogFrame";
import { IconButton } from "@/ui/primitives/IconButton/IconButton";
import styles from "./AssistantDialogs.module.css";

type AssistantEventDetailDialogProps = {
  message: AssistantMessage | null;
  onClose: () => void;
};

export function AssistantEventDetailDialog({
  message,
  onClose,
}: AssistantEventDetailDialogProps) {
  return (
    <Dialog open={message !== null} onOpenChange={(open) => !open && onClose()}>
      {message ? (
        <DialogFrame
          actions={
            <DialogClose asChild>
              <IconButton aria-label="Close event details">
                <X size={16} aria-hidden="true" />
              </IconButton>
            </DialogClose>
          }
          ariaLabel={message.detailTitle ?? eventLabel(message)}
          className={styles.content}
          eyebrow={eventLabel(message)}
          title={message.detailTitle ?? eventLabel(message)}
        >
          <p className={styles.meta}>{message.timestamp}</p>
          {isImageGenerationEvent(message) && imageGenerationDataUrl(message) ? (
            <img
              alt="Generated image"
              className={styles.image}
              src={imageGenerationDataUrl(message) ?? undefined}
            />
          ) : null}
          {isImageGenerationEvent(message) &&
          typeof imageGenerationPayload(message)?.revised_prompt === "string" ? (
            <pre className={styles.pre}>
              {String(imageGenerationPayload(message)?.revised_prompt)}
            </pre>
          ) : (
            <pre className={styles.pre}>{message.detailBody ?? message.content}</pre>
          )}
        </DialogFrame>
      ) : null}
    </Dialog>
  );
}

