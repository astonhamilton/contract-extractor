import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/ui/primitives/Button/Button";
import { Spinner } from "@/ui/primitives/Spinner/Spinner";
import styles from "./PaginationStatusControls.module.css";

type PaginationStatusControlsProps = {
  canGoNext: boolean;
  canGoPrevious: boolean;
  label: string;
  loading?: boolean;
  loadingLabel?: string;
  nextAriaLabel?: string;
  nextLabel?: string;
  onNext: () => void;
  onPrevious: () => void;
  previousAriaLabel?: string;
  previousLabel?: string;
  variant?: "ghost" | "secondary";
};

export function PaginationStatusControls({
  canGoNext,
  canGoPrevious,
  label,
  loading = false,
  loadingLabel,
  nextAriaLabel,
  nextLabel = "Next",
  onNext,
  onPrevious,
  previousAriaLabel,
  previousLabel = "Prev",
  variant = "secondary",
}: PaginationStatusControlsProps) {
  return (
    <div className={styles.root}>
      <Button
        aria-label={previousAriaLabel}
        className={styles.button}
        disabled={!canGoPrevious}
        onClick={onPrevious}
        variant={variant}
      >
        <ChevronLeft size={14} aria-hidden="true" />
        {previousLabel}
      </Button>
      <span className={styles.label}>{label}</span>
      <Button
        aria-label={nextAriaLabel}
        className={styles.button}
        disabled={!canGoNext}
        onClick={onNext}
        variant={variant}
      >
        {nextLabel}
        <ChevronRight size={14} aria-hidden="true" />
      </Button>
      <span
        aria-label={loading && loadingLabel ? loadingLabel : undefined}
        className={styles.loadingSlot}
        role={loading ? "status" : undefined}
      >
        {loading ? <Spinner /> : null}
      </span>
    </div>
  );
}
