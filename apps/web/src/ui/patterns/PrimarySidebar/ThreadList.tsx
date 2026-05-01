import { cn } from "@/lib/cn";
import type { AssistantThread } from "@/screens/AssistantScreen/AssistantScreen.types";
import styles from "./ThreadList.module.css";

type ThreadListProps = {
  collapsed: boolean;
  error: string | null;
  loading: boolean;
  onSelectThread: (threadId: string) => void;
  selectedThreadId: string | null;
  threads: AssistantThread[];
};

export function ThreadList({
  collapsed,
  error,
  loading = false,
  onSelectThread,
  selectedThreadId,
  threads = [],
}: ThreadListProps) {
  if (loading) {
    return (
      <div className={cn(styles.root, collapsed && styles.collapsed)}>
        <span className={collapsed ? styles.dot : styles.notice}>
          {collapsed ? "" : "Loading threads..."}
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn(styles.root, collapsed && styles.collapsed)}>
        <span className={collapsed ? styles.dot : styles.notice}>
          {collapsed ? "" : "Threads unavailable"}
        </span>
      </div>
    );
  }

  if (threads.length === 0) {
    return (
      <div className={cn(styles.root, collapsed && styles.collapsed)}>
        <span className={collapsed ? styles.dot : styles.notice}>
          {collapsed ? "" : "No threads yet"}
        </span>
      </div>
    );
  }

  if (collapsed) {
    return (
      <div className={cn(styles.root, styles.collapsed)} aria-label="Thread list">
        {threads.map((thread) => (
          <button
            key={thread.id}
            aria-label={thread.title}
            className={cn(
              styles.dotButton,
              thread.id === selectedThreadId && styles.dotButtonSelected,
            )}
            onClick={() => onSelectThread(thread.id)}
            title={thread.title}
            type="button"
          />
        ))}
      </div>
    );
  }

  return (
    <div className={styles.root} aria-label="Thread list">
      {threads.map((thread) => (
        <button
          key={thread.id}
          className={cn(
            styles.item,
            thread.id === selectedThreadId && styles.itemSelected,
          )}
          onClick={() => onSelectThread(thread.id)}
          type="button"
        >
          <span>{thread.title}</span>
          <small>{thread.summary}</small>
        </button>
      ))}
    </div>
  );
}
