import { Plus, RefreshCw } from "lucide-react";
import { IconButton } from "@/ui/primitives/IconButton/IconButton";
import { Spinner } from "@/ui/primitives/Spinner/Spinner";
import styles from "./ThreadHeader.module.css";

type ThreadHeaderProps = {
  collapsed: boolean;
  loading: boolean;
  onCreateThread: () => void;
  onRefreshThreads: () => Promise<void>;
};

export function ThreadHeader({
  collapsed,
  loading,
  onCreateThread,
  onRefreshThreads,
}: ThreadHeaderProps) {
  return (
    <div className={styles.root}>
      {collapsed ? null : <p className={styles.eyebrow}>Threads</p>}
      <div className={styles.actions}>
        {collapsed ? null : (
          <IconButton
            aria-label="Refresh threads"
            disabled={loading}
            onClick={() => {
              void onRefreshThreads();
            }}
            tooltip={loading ? "Refreshing threads" : "Refresh threads"}
          >
            {loading ? <Spinner /> : <RefreshCw size={15} aria-hidden="true" />}
          </IconButton>
        )}
        <IconButton
          aria-label="Create thread"
          onClick={onCreateThread}
          tooltip="Create thread"
        >
          <Plus size={16} aria-hidden="true" />
        </IconButton>
      </div>
    </div>
  );
}
