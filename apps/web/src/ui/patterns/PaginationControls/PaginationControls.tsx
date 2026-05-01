import { Button } from "@/ui/primitives/Button/Button";
import styles from "./PaginationControls.module.css";

type PaginationControlsProps = {
  label: string;
  canGoPrevious: boolean;
  canGoNext: boolean;
  onPrevious: () => void;
  onNext: () => void;
};

export function PaginationControls({
  canGoNext,
  canGoPrevious,
  label,
  onNext,
  onPrevious,
}: PaginationControlsProps) {
  return (
    <div className={styles.root}>
      <span className={styles.label}>{label}</span>
      <div className={styles.actions}>
        <Button disabled={!canGoPrevious} onClick={onPrevious}>
          Previous
        </Button>
        <Button disabled={!canGoNext} onClick={onNext}>
          Next
        </Button>
      </div>
    </div>
  );
}
