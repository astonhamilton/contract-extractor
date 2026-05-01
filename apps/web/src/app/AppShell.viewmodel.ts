import { useStoredState } from "@/lib/useStoredState";

export type AppShellViewModel = {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
};

export function useAppShellViewModel(): AppShellViewModel {
  const [sidebarCollapsed, setSidebarCollapsed] = useStoredState(
    "ci.web-v2.sidebarCollapsed",
    false,
    { storage: "session" },
  );

  return {
    sidebarCollapsed,
    toggleSidebar: () => setSidebarCollapsed((current) => !current),
  };
}
