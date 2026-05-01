import { useAssistantWorkspace } from "@/app/assistant/AssistantWorkspaceProvider";
import type {
  AssistantMessage,
  AssistantThread,
  AssistantTurn,
} from "@/screens/AssistantScreen/AssistantScreen.types";
import { useAssistantComposer } from "@/screens/AssistantScreen/hooks/useAssistantComposer";
import { useAssistantDialogs } from "@/screens/AssistantScreen/hooks/useAssistantDialogs";
import { useAssistantThreadItems } from "@/screens/AssistantScreen/hooks/useAssistantThreadItems";

export type AssistantScreenViewModel = {
  activeDebugMessage: AssistantMessage | null;
  activeEvent: AssistantMessage | null;
  activeImageMessage: AssistantMessage | null;
  activeTurn: AssistantTurn | null;
  draft: string;
  error: string | null;
  isRefreshing: boolean;
  isSending: boolean;
  isWorking: boolean;
  messages: AssistantMessage[];
  selectedThread: AssistantThread | null;
  status: "empty" | "loading" | "error" | "ready";
  actions: {
    closeDebug: () => void;
    closeEvent: () => void;
    closeImage: () => void;
    createThread: () => void;
    openDebug: (messageId: string) => void;
    openEvent: (messageId: string) => void;
    openImage: (messageId: string) => void;
    refreshThread: () => Promise<void>;
    sendMessage: () => Promise<void>;
    setDraft: (draft: string) => void;
  };
};

export function useAssistantScreenViewModel(): AssistantScreenViewModel {
  const workspace = useAssistantWorkspace();
  const {
    createDraftThread,
    refreshThreads,
    replaceDraftWithBackendThread,
    selectedThread,
    updateThread,
  } = workspace;
  const threadItems = useAssistantThreadItems({
    refreshThreads,
    selectedThread,
    updateThread,
  });
  const composer = useAssistantComposer({
    replaceDraftWithBackendThread,
    selectedThread,
    updateThread,
  });
  const dialogs = useAssistantDialogs(threadItems.messages);

  return {
    activeDebugMessage: dialogs.activeDebugMessage,
    activeEvent: dialogs.activeEvent,
    activeImageMessage: dialogs.activeImageMessage,
    activeTurn: threadItems.activeTurn,
    draft: composer.draft,
    error: threadItems.error,
    isRefreshing: threadItems.isRefreshing,
    isSending: composer.isSending,
    isWorking: composer.isSending || threadItems.isWorking,
    messages: threadItems.messages,
    selectedThread,
    status: threadItems.status,
    actions: {
      closeDebug: dialogs.actions.closeDebug,
      closeEvent: dialogs.actions.closeEvent,
      closeImage: dialogs.actions.closeImage,
      createThread: createDraftThread,
      openDebug: dialogs.actions.openDebug,
      openEvent: dialogs.actions.openEvent,
      openImage: dialogs.actions.openImage,
      refreshThread: threadItems.refreshThread,
      sendMessage: composer.sendMessage,
      setDraft: composer.setDraft,
    },
  };
}
