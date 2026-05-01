import { cn } from "@/lib/cn";
import styles from "./Spinner.module.css";

type SpinnerProps = {
  className?: string;
};

export function Spinner({ className }: SpinnerProps) {
  return <span aria-hidden="true" className={cn(styles.root, className)} />;
}
