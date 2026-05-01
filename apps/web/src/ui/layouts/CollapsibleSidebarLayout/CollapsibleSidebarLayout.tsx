import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import styles from "./CollapsibleSidebarLayout.module.css";

type CollapsibleSidebarLayoutProps = {
  collapsed: boolean;
  left: ReactNode;
  right: ReactNode;
};

export function CollapsibleSidebarLayout({
  collapsed,
  left,
  right,
}: CollapsibleSidebarLayoutProps) {
  return (
    <div
      className={cn(
        styles.root,
        collapsed && styles.collapsed,
      )}
    >
      <aside className={styles.left}>{left}</aside>
      <main className={styles.right}>{right}</main>
    </div>
  );
}
