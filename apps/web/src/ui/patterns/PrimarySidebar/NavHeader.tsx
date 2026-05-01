import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { cn } from "@/lib/cn";
import { IconButton } from "@/ui/primitives/IconButton/IconButton";
import styles from "./NavHeader.module.css";

type NavHeaderProps = {
  collapsed: boolean;
  onToggleCollapsed: () => void;
};

export function NavHeader({ collapsed, onToggleCollapsed }: NavHeaderProps) {
  return (
    <header className={cn(styles.root, collapsed && styles.collapsed)}>
      <span className={styles.mark} aria-hidden="true">
        CI
      </span>
      {collapsed ? null : (
        <span className={styles.title}>Contract Intelligence</span>
      )}
      <IconButton
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        className={styles.collapseButton}
        onClick={onToggleCollapsed}
        tooltip={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? (
          <PanelLeftOpen size={16} aria-hidden="true" />
        ) : (
          <PanelLeftClose size={16} aria-hidden="true" />
        )}
      </IconButton>
    </header>
  );
}
