import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";
import styles from "./TextField.module.css";

type TextFieldProps = InputHTMLAttributes<HTMLInputElement>;

export function TextField({ className, ...props }: TextFieldProps) {
  return <input className={cn(styles.root, className)} {...props} />;
}
