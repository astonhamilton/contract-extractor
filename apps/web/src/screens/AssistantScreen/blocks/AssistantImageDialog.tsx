import { X } from "lucide-react";
import {
  imageGenerationDataUrl,
  imageGenerationPayload,
} from "@/screens/AssistantScreen/AssistantScreen.helpers";
import type { AssistantMessage } from "@/screens/AssistantScreen/AssistantScreen.types";
import { Dialog, DialogClose } from "@/ui/primitives/Dialog/Dialog";
import { DialogFrame } from "@/ui/patterns/DialogFrame/DialogFrame";
import { IconButton } from "@/ui/primitives/IconButton/IconButton";
import styles from "./AssistantDialogs.module.css";

type AssistantImageDialogProps = {
  message: AssistantMessage | null;
  onClose: () => void;
};

export function AssistantImageDialog({
  message,
  onClose,
}: AssistantImageDialogProps) {
  const imageUrl = message ? imageGenerationDataUrl(message) : null;

  return (
    <Dialog open={imageUrl !== null} onOpenChange={(open) => !open && onClose()}>
      {message && imageUrl ? (
        <DialogFrame
          actions={
            <DialogClose asChild>
              <IconButton aria-label="Close image preview">
                <X size={16} aria-hidden="true" />
              </IconButton>
            </DialogClose>
          }
          ariaLabel="Generated image"
          className={styles.wideContent}
          eyebrow="Generated image"
          title={message.detailTitle ?? message.title}
        >
          <img alt="Generated image" className={styles.imageLarge} src={imageUrl} />
          {typeof imageGenerationPayload(message)?.revised_prompt === "string" ? (
            <p className={styles.meta}>
              {String(imageGenerationPayload(message)?.revised_prompt)}
            </p>
          ) : null}
        </DialogFrame>
      ) : null}
    </Dialog>
  );
}

