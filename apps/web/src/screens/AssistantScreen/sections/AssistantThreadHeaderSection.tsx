import { Plus, RefreshCw } from "lucide-react";
import type { AssistantThread, AssistantTurn } from "@/screens/AssistantScreen/AssistantScreen.types";
import { Button } from "@/ui/primitives/Button/Button";
import { IconButton } from "@/ui/primitives/IconButton/IconButton";
import { Spinner } from "@/ui/primitives/Spinner/Spinner";
import styles from "./AssistantThreadHeaderSection.module.css";

type AssistantThreadHeaderSectionProps = {
  activeTurn: AssistantTurn | null;
  isRefreshing: boolean;
  isWorking: boolean;
  onCreateThread: () => void;
  onRefreshThread: () => Promise<void>;
  selectedThread: AssistantThread | null;
};

export function AssistantThreadHeaderSection({
  activeTurn,
  isRefreshing,
  isWorking,
  onCreateThread,
  onRefreshThread,
  selectedThread,
}: AssistantThreadHeaderSectionProps) {
  return (
    <header className={styles.root}>
      <div className={styles.copy}>
        <p className={styles.eyebrow}>Assistant</p>
        <h1 className={styles.title}>
          {selectedThread?.title ?? "Ask Assistant"}
        </h1>
        <p className={styles.meta}>
          {selectedThread
            ? activeTurn
              ? `Working on turn ${activeTurn.turn_id}`
              : `Updated ${selectedThread.updatedAt}`
            : "Create or select a thread to start."}
        </p>
      </div>
      <div className={styles.actions}>
        {isWorking ? (
          <span className={styles.status}>
            <Spinner />
            Working
          </span>
        ) : null}
        <IconButton
          aria-label="Refresh thread"
          disabled={!selectedThread || isRefreshing}
          onClick={() => {
            void onRefreshThread();
          }}
          tooltip={isRefreshing ? "Refreshing thread" : "Refresh thread"}
        >
          {isRefreshing ? <Spinner /> : <RefreshCw size={16} aria-hidden="true" />}
        </IconButton>
        <Button onClick={onCreateThread} variant="primary">
          <Plus size={16} aria-hidden="true" />
          New thread
        </Button>
      </div>
    </header>
  );
}
