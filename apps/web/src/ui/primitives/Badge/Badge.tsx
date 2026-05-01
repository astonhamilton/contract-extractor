import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import styles from "./Badge.module.css";

type BadgeTone = "neutral" | "accent" | "success" | "warning";

type BadgeProps = {
  children: ReactNode;
  tone?: BadgeTone;
};

export function Badge({ children, tone = "neutral" }: BadgeProps) {
  return <span className={cn(styles.root, styles[tone])}>{children}</span>;
}
