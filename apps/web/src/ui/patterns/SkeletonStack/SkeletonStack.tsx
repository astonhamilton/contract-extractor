import styles from "./SkeletonStack.module.css";

type SkeletonStackProps = {
  rows?: number;
};

export function SkeletonStack({ rows = 4 }: SkeletonStackProps) {
  return (
    <div className={styles.root} aria-label="Loading" role="status">
      {Array.from({ length: rows }).map((_, index) => (
        <span key={index} className={styles.line} />
      ))}
    </div>
  );
}
