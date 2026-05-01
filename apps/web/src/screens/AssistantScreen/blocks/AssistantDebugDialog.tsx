import { X } from "lucide-react";
import type { AssistantMessage } from "@/screens/AssistantScreen/AssistantScreen.types";
import { Dialog, DialogClose } from "@/ui/primitives/Dialog/Dialog";
import { DialogFrame } from "@/ui/patterns/DialogFrame/DialogFrame";
import { IconButton } from "@/ui/primitives/IconButton/IconButton";
import styles from "./AssistantDialogs.module.css";

type AssistantDebugDialogProps = {
  message: AssistantMessage | null;
  onClose: () => void;
};

export function AssistantDebugDialog({
  message,
  onClose,
}: AssistantDebugDialogProps) {
  return (
    <Dialog open={message !== null} onOpenChange={(open) => !open && onClose()}>
      {message ? (
        <DialogFrame
          actions={
            <DialogClose asChild>
              <IconButton aria-label="Close debug JSON">
                <X size={16} aria-hidden="true" />
              </IconButton>
            </DialogClose>
          }
          ariaLabel="Raw item JSON"
          className={styles.content}
          eyebrow="Debug"
          title="Raw item JSON"
        >
          <p className={styles.meta}>{message.timestamp}</p>
          <pre className={styles.pre}>
            {message.rawJson ?? JSON.stringify(message, null, 2)}
          </pre>
        </DialogFrame>
      ) : null}
    </Dialog>
  );
}

