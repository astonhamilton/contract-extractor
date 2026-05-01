import { AssistantComposerSection } from "@/screens/AssistantScreen/sections/AssistantComposerSection";
import { AssistantThreadHeaderSection } from "@/screens/AssistantScreen/sections/AssistantThreadHeaderSection";
import { AssistantTranscriptSection } from "@/screens/AssistantScreen/sections/AssistantTranscriptSection";
import { AssistantDebugDialog } from "@/screens/AssistantScreen/blocks/AssistantDebugDialog";
import { AssistantEventDetailDialog } from "@/screens/AssistantScreen/blocks/AssistantEventDetailDialog";
import { AssistantImageDialog } from "@/screens/AssistantScreen/blocks/AssistantImageDialog";
import { useAssistantScreenViewModel } from "@/screens/AssistantScreen/AssistantScreen.viewmodel";
import { ScreenLayout } from "@/ui/layouts/ScreenLayout/ScreenLayout";
import styles from "./AssistantScreen.module.css";

export function AssistantScreen() {
  const assistant = useAssistantScreenViewModel();

  return (
    <ScreenLayout contentInset="none">
      <div className={styles.root}>
        <AssistantThreadHeaderSection
          activeTurn={assistant.activeTurn}
          isRefreshing={assistant.isRefreshing}
          isWorking={assistant.isWorking}
          onCreateThread={assistant.actions.createThread}
          onRefreshThread={assistant.actions.refreshThread}
          selectedThread={assistant.selectedThread}
        />
        <AssistantTranscriptSection
          error={assistant.error}
          isWorking={assistant.isWorking}
          messages={assistant.messages}
          onCreateThread={assistant.actions.createThread}
          onOpenDebug={assistant.actions.openDebug}
          onOpenEvent={assistant.actions.openEvent}
          onOpenImage={assistant.actions.openImage}
          status={assistant.status}
        />
        <AssistantComposerSection
          disabled={!assistant.selectedThread || assistant.isSending}
          draft={assistant.draft}
          isSending={assistant.isSending}
          onDraftChange={assistant.actions.setDraft}
          onSendMessage={assistant.actions.sendMessage}
        />
      </div>
      <AssistantEventDetailDialog
        message={assistant.activeEvent}
        onClose={assistant.actions.closeEvent}
      />
      <AssistantDebugDialog
        message={assistant.activeDebugMessage}
        onClose={assistant.actions.closeDebug}
      />
      <AssistantImageDialog
        message={assistant.activeImageMessage}
        onClose={assistant.actions.closeImage}
      />
    </ScreenLayout>
  );
}
