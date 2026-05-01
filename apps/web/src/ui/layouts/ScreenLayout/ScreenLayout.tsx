import type { ReactNode } from "react";
import styles from "./ScreenLayout.module.css";

type ScreenLayoutProps = {
  header?: ReactNode;
  children: ReactNode;
  contentInset?: "default" | "none";
};

export function ScreenLayout({
  children,
  contentInset = "default",
  header,
}: ScreenLayoutProps) {
  return (
    <section className={styles.root}>
      {header ?? null}
      <div className={styles.content} data-inset={contentInset}>
        {children}
      </div>
    </section>
  );
}
