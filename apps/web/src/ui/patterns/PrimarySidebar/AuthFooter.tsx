import { LogOut } from "lucide-react";
import type { AuthSessionUser } from "@/services/auth/authApi";
import { Badge } from "@/ui/primitives/Badge/Badge";
import { IconButton } from "@/ui/primitives/IconButton/IconButton";
import styles from "./AuthFooter.module.css";

type AuthFooterProps = {
  authEnabled: boolean;
  collapsed: boolean;
  loading: boolean;
  logoutPending: boolean;
  onLogout: () => Promise<void>;
  user: AuthSessionUser | null;
};

function initialsFor(user: AuthSessionUser | null): string {
  if (!user) {
    return "?";
  }

  const parts = user.display_name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return user.email.slice(0, 1).toUpperCase();
  }
  return parts
    .slice(0, 2)
    .map((part) => part.slice(0, 1).toUpperCase())
    .join("");
}

function sessionLabel({
  authEnabled,
  loading,
  user,
}: Pick<AuthFooterProps, "authEnabled" | "loading" | "user">): string {
  if (!authEnabled) {
    return "Auth disabled";
  }
  if (loading) {
    return "Checking session";
  }
  if (user) {
    return user.group_name;
  }
  return "Signed out";
}

export function AuthFooter({
  authEnabled,
  collapsed,
  loading,
  logoutPending,
  onLogout,
  user,
}: AuthFooterProps) {
  const label = sessionLabel({ authEnabled, loading, user });

  return (
    <footer className={styles.root}>
      <span className={styles.avatar} aria-hidden="true">
        {initialsFor(user)}
      </span>
      {collapsed ? null : (
        <div className={styles.copy}>
          <span className={styles.label}>{user?.display_name ?? "Session"}</span>
          <Badge tone="neutral">{label}</Badge>
        </div>
      )}
      {!collapsed && user ? (
        <IconButton
          aria-label="Sign out"
          disabled={logoutPending}
          onClick={() => {
            void onLogout();
          }}
          tooltip="Sign out"
        >
          <LogOut size={15} aria-hidden="true" />
        </IconButton>
      ) : null}
    </footer>
  );
}
