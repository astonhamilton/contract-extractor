import type { ReactNode } from "react";
import styles from "./MainNavSection.module.css";

type MainNavSectionProps = {
  children: ReactNode;
  collapsed: boolean;
};

export function MainNavSection({ children, collapsed }: MainNavSectionProps) {
  return (
    <section className={styles.root} aria-label="Main navigation">
      {collapsed ? null : <p className={styles.eyebrow}>Browse</p>}
      <nav className={styles.items}>{children}</nav>
    </section>
  );
}
