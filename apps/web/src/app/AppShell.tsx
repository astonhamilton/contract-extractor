import { Outlet } from "react-router-dom";
import { AssistantWorkspaceProvider, useAssistantWorkspace } from "@/app/assistant/AssistantWorkspaceProvider";
import { useAppShellViewModel } from "@/app/AppShell.viewmodel";
import { useAuth } from "@/app/auth/AuthProvider";
import { CollapsibleSidebarLayout } from "@/ui/layouts/CollapsibleSidebarLayout/CollapsibleSidebarLayout";
import { PrimarySidebar } from "@/ui/patterns/PrimarySidebar/PrimarySidebar";

export function AppShell() {
  return (
    <AssistantWorkspaceProvider>
      <AppShellContent />
    </AssistantWorkspaceProvider>
  );
}

function AppShellContent() {
  const shell = useAppShellViewModel();
  const auth = useAuth();
  const assistant = useAssistantWorkspace();

  return (
    <CollapsibleSidebarLayout
      collapsed={shell.sidebarCollapsed}
      left={
        <PrimarySidebar
          authEnabled={auth.enabled}
          authLoading={auth.isLoading}
          authUser={auth.user}
          collapsed={shell.sidebarCollapsed}
          logoutPending={auth.isLogoutPending}
          onToggleCollapsed={shell.toggleSidebar}
          onLogout={auth.logout}
          onCreateThread={assistant.createDraftThread}
          onRefreshThreads={assistant.refreshThreads}
          onSelectThread={assistant.selectThread}
          selectedThreadId={assistant.selectedThreadId}
          threads={assistant.threads}
          threadsError={assistant.threadsError}
          threadsLoading={assistant.threadsLoading}
          threadsRefreshing={assistant.threadsRefreshing}
        />
      }
      right={<Outlet />}
    />
  );
}
