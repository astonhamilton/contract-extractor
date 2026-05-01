import type { ReactNode } from "react";
import {
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/ui/primitives/Dialog/Dialog";
import { cn } from "@/lib/cn";
import styles from "./DialogFrame.module.css";

type DialogFrameProps = {
  actions?: ReactNode;
  ariaLabel: string;
  children: ReactNode;
  className?: string;
  description?: ReactNode;
  eyebrow?: string;
  title: ReactNode;
};

export function DialogFrame({
  actions,
  ariaLabel,
  children,
  className,
  description,
  eyebrow,
  title,
}: DialogFrameProps) {
  return (
    <DialogContent aria-label={ariaLabel} className={cn(styles.content, className)}>
      <div className={styles.header}>
        <div>
          {eyebrow ? <p className={styles.eyebrow}>{eyebrow}</p> : null}
          <DialogTitle className={styles.title}>{title}</DialogTitle>
          <DialogDescription className={styles.description}>
            {description ?? ariaLabel}
          </DialogDescription>
        </div>
        {actions ? <div className={styles.actions}>{actions}</div> : null}
      </div>
      <div className={styles.body}>{children}</div>
    </DialogContent>
  );
}
