import type { CSSProperties, ReactNode } from "react";
import { cn } from "@/lib/cn";
import styles from "./Flex.module.css";

type FlexProps = {
  children: ReactNode;
  align?: CSSProperties["alignItems"];
  className?: string;
  direction?: "row" | "column";
  fill?: boolean;
  gap?: "none" | "xs" | "sm" | "md" | "lg";
  justify?: CSSProperties["justifyContent"];
};

export function Flex({
  align,
  children,
  className,
  direction = "row",
  fill = false,
  gap = "none",
  justify,
}: FlexProps) {
  const gapClass = {
    none: null,
    xs: styles.gapXs,
    sm: styles.gapSm,
    md: styles.gapMd,
    lg: styles.gapLg,
  }[gap];

  return (
    <div
      className={cn(
        styles.root,
        direction === "row" ? styles.row : styles.column,
        gapClass,
        fill && styles.fill,
        className,
      )}
      style={{ alignItems: align, justifyContent: justify }}
    >
      {children}
    </div>
  );
}
