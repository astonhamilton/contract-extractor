import type { ReactNode } from "react";
import styles from "./Toolbar.module.css";

type ToolbarProps = {
  children: ReactNode;
  footer?: ReactNode;
};

export function Toolbar({ children, footer }: ToolbarProps) {
  return (
    <div className={styles.root}>
      <div className={styles.controls}>{children}</div>
      {footer ? <div className={styles.footer}>{footer}</div> : null}
    </div>
  );
}
