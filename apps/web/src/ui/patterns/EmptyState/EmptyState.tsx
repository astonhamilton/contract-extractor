import type { ReactNode } from "react";
import styles from "./EmptyState.module.css";

type EmptyStateProps = {
  eyebrow?: string;
  title: string;
  children?: ReactNode;
  actions?: ReactNode;
};

export function EmptyState({ actions, children, eyebrow, title }: EmptyStateProps) {
  return (
    <div className={styles.root}>
      {eyebrow ? <p className={styles.eyebrow}>{eyebrow}</p> : null}
      <h3 className={styles.title}>{title}</h3>
      {children ? <div className={styles.copy}>{children}</div> : null}
      {actions ? <div className={styles.actions}>{actions}</div> : null}
    </div>
  );
}
