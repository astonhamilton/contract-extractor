import type { ReactNode } from "react";
import styles from "./WorkspaceSplit.module.css";

type WorkspaceSplitProps = {
  sidebar: ReactNode;
  content: ReactNode;
};

export function WorkspaceSplit({ content, sidebar }: WorkspaceSplitProps) {
  return (
    <div className={styles.root}>
      <aside className={styles.sidebar}>{sidebar}</aside>
      <section className={styles.content}>{content}</section>
    </div>
  );
}
