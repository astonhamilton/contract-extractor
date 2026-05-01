import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import styles from "./DefinitionGrid.module.css";

export type DefinitionGridItem = {
  label: string;
  value: ReactNode;
  missing?: boolean;
};

type DefinitionGridProps = {
  className?: string;
  items: DefinitionGridItem[];
  variant?: "cards" | "table";
};

export function DefinitionGrid({
  className,
  items,
  variant = "cards",
}: DefinitionGridProps) {
  return (
    <dl className={cn(styles.root, styles[variant], className)}>
      {items.map((item) => (
        <div key={item.label} className={styles.item}>
          <dt>{item.label}</dt>
          <dd className={item.missing ? styles.missing : undefined}>
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
