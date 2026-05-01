import type { ReactNode } from "react";
import styles from "./ResultList.module.css";

type ResultListProps = {
  children: ReactNode;
  label: string;
};

export function ResultList({ children, label }: ResultListProps) {
  return (
    <div className={styles.root} role="list" aria-label={label}>
      {children}
    </div>
  );
}

export function ResultListGroup({ children }: { children: ReactNode }) {
  return <div className={styles.group}>{children}</div>;
}

export function ResultListGroupHeader({ children }: { children: ReactNode }) {
  return <div className={styles.groupHeader}>{children}</div>;
}
