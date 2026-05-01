import type { ReactNode } from "react";
import styles from "./InspectorPane.module.css";

type InspectorPaneProps = {
  children: ReactNode;
};

export function InspectorPane({ children }: InspectorPaneProps) {
  return <div className={styles.root}>{children}</div>;
}

export function InspectorPaneHeader({ children }: InspectorPaneProps) {
  return <header className={styles.header}>{children}</header>;
}

export function InspectorPaneBody({ children }: InspectorPaneProps) {
  return <div className={styles.body}>{children}</div>;
}
