import { useMemo, useState } from "react";
import type { AssistantMessage } from "@/screens/AssistantScreen/AssistantScreen.types";

export type AssistantDialogState = {
  activeDebugMessage: AssistantMessage | null;
  activeEvent: AssistantMessage | null;
  activeImageMessage: AssistantMessage | null;
  actions: {
    closeDebug: () => void;
    closeEvent: () => void;
    closeImage: () => void;
    openDebug: (messageId: string) => void;
    openEvent: (messageId: string) => void;
    openImage: (messageId: string) => void;
  };
};

export function useAssistantDialogs(
  messages: AssistantMessage[],
): AssistantDialogState {
  const [activeEventId, setActiveEventId] = useState<string | null>(null);
  const [activeDebugId, setActiveDebugId] = useState<string | null>(null);
  const [activeImageId, setActiveImageId] = useState<string | null>(null);

  const activeEvent = useMemo(
    () => messages.find((message) => message.id === activeEventId) ?? null,
    [activeEventId, messages],
  );
  const activeDebugMessage = useMemo(
    () => messages.find((message) => message.id === activeDebugId) ?? null,
    [activeDebugId, messages],
  );
  const activeImageMessage = useMemo(
    () => messages.find((message) => message.id === activeImageId) ?? null,
    [activeImageId, messages],
  );

  return {
    activeDebugMessage,
    activeEvent,
    activeImageMessage,
    actions: {
      closeDebug: () => setActiveDebugId(null),
      closeEvent: () => setActiveEventId(null),
      closeImage: () => setActiveImageId(null),
      openDebug: setActiveDebugId,
      openEvent: setActiveEventId,
      openImage: setActiveImageId,
    },
  };
}
