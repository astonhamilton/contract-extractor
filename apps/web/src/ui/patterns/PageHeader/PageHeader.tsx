import type { ReactNode } from "react";
import styles from "./PageHeader.module.css";

type PageHeaderProps = {
  actions?: ReactNode;
  eyebrow?: string;
  lede?: string;
  title: string;
  titleId?: string;
};

export function PageHeader({
  actions,
  eyebrow,
  lede,
  title,
  titleId,
}: PageHeaderProps) {
  return (
    <header className={styles.root}>
      <div className={styles.copy}>
        {eyebrow ? <p className={styles.eyebrow}>{eyebrow}</p> : null}
        <h1 className={styles.title} id={titleId}>
          {title}
        </h1>
        {lede ? <p className={styles.lede}>{lede}</p> : null}
      </div>
      {actions ? <div className={styles.actions}>{actions}</div> : null}
    </header>
  );
}
