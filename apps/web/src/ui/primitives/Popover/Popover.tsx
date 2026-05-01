import * as PopoverPrimitive from "@radix-ui/react-popover";
import { cn } from "@/lib/cn";
import styles from "./Popover.module.css";

export const Popover = PopoverPrimitive.Root;
export const PopoverTrigger = PopoverPrimitive.Trigger;
export const PopoverPortal = PopoverPrimitive.Portal;
export const PopoverClose = PopoverPrimitive.Close;

export function PopoverContent({
  children,
  className,
  ...props
}: PopoverPrimitive.PopoverContentProps) {
  return (
    <PopoverPortal>
      <PopoverPrimitive.Content
        className={cn(styles.content, className)}
        sideOffset={8}
        {...props}
      >
        {children}
      </PopoverPrimitive.Content>
    </PopoverPortal>
  );
}
