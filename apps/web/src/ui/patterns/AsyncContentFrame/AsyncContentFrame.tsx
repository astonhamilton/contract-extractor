import {
  type ReactNode,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { cn } from "@/lib/cn";
import styles from "./AsyncContentFrame.module.css";

type AsyncContentFrameProps = {
  children: ReactNode;
  className?: string;
  contentClassName?: string;
  measuring: boolean;
  reset?: boolean;
};

export function AsyncContentFrame({
  children,
  className,
  contentClassName,
  measuring,
  reset = false,
}: AsyncContentFrameProps) {
  const [lastMeasuredHeight, setLastMeasuredHeight] = useState(0);
  const contentRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (reset) {
      setLastMeasuredHeight(0);
    }
  }, [reset]);

  useLayoutEffect(() => {
    if (!measuring || !contentRef.current) {
      return;
    }

    const content = contentRef.current;
    const updateHeight = () => {
      setLastMeasuredHeight(Math.ceil(content.getBoundingClientRect().height));
    };
    updateHeight();

    const observer = new ResizeObserver(updateHeight);
    observer.observe(content);
    return () => observer.disconnect();
  }, [measuring]);

  return (
    <div
      className={cn(styles.root, className)}
      style={lastMeasuredHeight > 0 ? { minHeight: lastMeasuredHeight } : undefined}
    >
      <div className={cn(styles.content, contentClassName)} ref={contentRef}>
        {children}
      </div>
    </div>
  );
}
