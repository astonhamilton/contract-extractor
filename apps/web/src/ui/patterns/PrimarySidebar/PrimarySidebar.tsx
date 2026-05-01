import {
  FileStack,
  LogOut,
  MessageSquare,
  MoreVertical,
  Plus,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import type { AssistantThread } from "@/screens/AssistantScreen/AssistantScreen.types";
import type { AuthSessionUser } from "@/services/auth/authApi";
import { AuthFooter } from "@/ui/patterns/PrimarySidebar/AuthFooter";
import { MainNavSection } from "@/ui/patterns/PrimarySidebar/MainNavSection";
import { NavHeader } from "@/ui/patterns/PrimarySidebar/NavHeader";
import { NavItem } from "@/ui/patterns/PrimarySidebar/NavItem";
import { ThreadHeader } from "@/ui/patterns/PrimarySidebar/ThreadHeader";
import { ThreadList } from "@/ui/patterns/PrimarySidebar/ThreadList";
import { cn } from "@/lib/cn";
import { IconButton } from "@/ui/primitives/IconButton/IconButton";
import {
  Popover,
  PopoverClose,
  PopoverContent,
  PopoverTrigger,
} from "@/ui/primitives/Popover/Popover";
import styles from "./PrimarySidebar.module.css";

type PrimarySidebarProps = {
  authEnabled: boolean;
  authLoading: boolean;
  authUser: AuthSessionUser | null;
  collapsed: boolean;
  logoutPending: boolean;
  onCreateThread: () => void;
  onRefreshThreads: () => Promise<void>;
  onSelectThread: (threadId: string) => void;
  onToggleCollapsed: () => void;
  onLogout: () => Promise<void>;
  selectedThreadId: string | null;
  threads: AssistantThread[];
  threadsError: string | null;
  threadsLoading: boolean;
  threadsRefreshing: boolean;
};

export function PrimarySidebar({
  authEnabled,
  authLoading,
  authUser,
  collapsed,
  logoutPending,
  onCreateThread,
  onRefreshThreads,
  onSelectThread,
  onToggleCollapsed,
  onLogout,
  selectedThreadId,
  threads,
  threadsError,
  threadsLoading,
  threadsRefreshing,
}: PrimarySidebarProps) {
  return (
    <div className={cn(styles.root, collapsed && styles.collapsed)}>
      <div className={styles.mobileBar}>
        <span className={styles.mobileMark} aria-hidden="true">
          CI
        </span>
        <span className={styles.mobileTitle}>Contract Intelligence</span>
        <Popover>
          <PopoverTrigger asChild>
            <IconButton aria-label="Open navigation menu">
              <MoreVertical size={18} aria-hidden="true" />
            </IconButton>
          </PopoverTrigger>
          <PopoverContent align="end" className={styles.mobileMenu}>
            <nav className={styles.mobileMenuGroup} aria-label="Main navigation">
              <PopoverClose asChild>
                <NavLink to="/corpus" className={styles.mobileMenuItem}>
                  <FileStack size={16} aria-hidden="true" />
                  Browse
                </NavLink>
              </PopoverClose>
              <PopoverClose asChild>
                <NavLink to="/assistant" className={styles.mobileMenuItem}>
                  <MessageSquare size={16} aria-hidden="true" />
                  Assistant
                </NavLink>
              </PopoverClose>
            </nav>
            <div className={styles.mobileMenuGroup}>
              <button
                className={styles.mobileMenuItem}
                onClick={onCreateThread}
                type="button"
              >
                <Plus size={16} aria-hidden="true" />
                Create thread
              </button>
            </div>
            <div className={styles.mobileSession}>
              <span className={styles.mobileSessionLabel}>
                {authUser?.display_name ?? "Session"}
              </span>
              <span className={styles.mobileSessionMeta}>
                {authEnabled
                  ? authLoading
                    ? "Checking session"
                    : authUser?.group_name ?? "Signed out"
                  : "Auth disabled"}
              </span>
              {authUser ? (
                <button
                  className={styles.mobileMenuItem}
                  disabled={logoutPending}
                  onClick={() => {
                    void onLogout();
                  }}
                  type="button"
                >
                  <LogOut size={16} aria-hidden="true" />
                  Sign out
                </button>
              ) : null}
            </div>
          </PopoverContent>
        </Popover>
      </div>

      <div className={styles.desktopRail}>
        <NavHeader collapsed={collapsed} onToggleCollapsed={onToggleCollapsed} />
        <MainNavSection collapsed={collapsed}>
          <NavItem
            collapsed={collapsed}
            icon={<FileStack size={16} aria-hidden="true" />}
            to="/corpus"
          >
            Browse Documents
          </NavItem>
          <NavItem
            collapsed={collapsed}
            icon={<MessageSquare size={16} aria-hidden="true" />}
            to="/assistant"
          >
            Assistant
          </NavItem>
        </MainNavSection>
        <section className={styles.threadSection} aria-label="Threads">
          <ThreadHeader
            collapsed={collapsed}
            loading={threadsRefreshing}
            onCreateThread={onCreateThread}
            onRefreshThreads={onRefreshThreads}
          />
          <ThreadList
            collapsed={collapsed}
            error={threadsError}
            loading={threadsLoading}
            onSelectThread={onSelectThread}
            selectedThreadId={selectedThreadId}
            threads={threads}
          />
        </section>
        <AuthFooter
          authEnabled={authEnabled}
          collapsed={collapsed}
          loading={authLoading}
          logoutPending={logoutPending}
          onLogout={onLogout}
          user={authUser}
        />
      </div>
    </div>
  );
}
