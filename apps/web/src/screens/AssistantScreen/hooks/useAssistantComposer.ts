import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  assistantThreadFromCreateApi,
  assistantThreadFromPostApi,
  optimisticUserMessage,
} from "@/screens/AssistantScreen/AssistantScreen.adapters";
import type { AssistantThread } from "@/screens/AssistantScreen/AssistantScreen.types";
import {
  createAssistantThread,
  postAssistantThreadMessage,
} from "@/services/assistant/assistantApi";
import { assistantKeys } from "@/services/assistant/assistantQueries";
import { useStoredState } from "@/lib/useStoredState";

export type AssistantComposerState = {
  draft: string;
  isSending: boolean;
  sendMessage: () => Promise<void>;
  setDraft: (draft: string) => void;
};

type AssistantComposerOptions = {
  replaceDraftWithBackendThread: (
    draftThreadId: string,
    backendThread: AssistantThread,
  ) => void;
  selectedThread: AssistantThread | null;
  updateThread: (
    threadId: string,
    updater: (thread: AssistantThread) => AssistantThread,
  ) => void;
};

export function useAssistantComposer({
  replaceDraftWithBackendThread,
  selectedThread,
  updateThread,
}: AssistantComposerOptions): AssistantComposerState {
  const queryClient = useQueryClient();
  const [isSending, setIsSending] = useState(false);
  const [draftsByThread, setDraftsByThread] = useStoredState<
    Record<string, string>
  >("ci.assistant.drafts", {}, { storage: "session" });
  const draft = selectedThread ? draftsByThread[selectedThread.id] ?? "" : "";

  function setDraft(draftValue: string): void {
    if (!selectedThread) {
      return;
    }
    setDraftsByThread((current) => ({
      ...current,
      [selectedThread.id]: draftValue,
    }));
  }

  async function sendMessage(): Promise<void> {
    if (!selectedThread) {
      return;
    }
    const trimmed = draft.trim();
    if (!trimmed) {
      return;
    }

    const userMessage = optimisticUserMessage(trimmed);
    setDraftsByThread((current) => ({ ...current, [selectedThread.id]: "" }));
    updateThread(selectedThread.id, (current) => ({
      ...current,
      status: current.isDraft ? "retrieving" : "streaming",
      summary: trimmed,
      updatedAt: "just now",
      messages: [...current.messages, userMessage],
      itemsLoaded: true,
    }));
    setIsSending(true);

    try {
      if (selectedThread.isDraft || selectedThread.backendThreadId === null) {
        const response = await createAssistantThread(trimmed);
        const backendThread = assistantThreadFromCreateApi(response, {
          ...selectedThread,
          id: response.thread.thread_id,
          backendThreadId: response.thread.thread_id,
          messages: [userMessage],
          status: "streaming",
          summary: trimmed,
          isDraft: false,
          itemsLoaded: false,
        });
        replaceDraftWithBackendThread(selectedThread.id, backendThread);
      } else {
        const response = await postAssistantThreadMessage(
          selectedThread.backendThreadId,
          trimmed,
        );
        updateThread(selectedThread.id, (current) => ({
          ...current,
          ...assistantThreadFromPostApi(response, current),
          status: "streaming",
          summary: trimmed,
        }));
      }

      await queryClient.invalidateQueries({ queryKey: assistantKeys.threads() });
    } catch {
      updateThread(selectedThread.id, (current) => ({
        ...current,
        status: "error",
        summary: current.isDraft
          ? "Could not start this thread. Try sending again."
          : current.summary,
      }));
    } finally {
      setIsSending(false);
    }
  }

  return {
    draft,
    isSending,
    sendMessage,
    setDraft,
  };
}
