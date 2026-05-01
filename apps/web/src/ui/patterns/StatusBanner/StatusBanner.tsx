import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import styles from "./StatusBanner.module.css";

type StatusBannerTone = "neutral" | "warning" | "danger";

type StatusBannerProps = {
  children: ReactNode;
  tone?: StatusBannerTone;
};

export function StatusBanner({ children, tone = "neutral" }: StatusBannerProps) {
  return <div className={cn(styles.root, styles[tone])}>{children}</div>;
}
