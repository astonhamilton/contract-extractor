import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { cn } from "@/lib/cn";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/ui/primitives/Tooltip/Tooltip";
import styles from "./NavItem.module.css";

type NavItemProps = {
  children: ReactNode;
  collapsed: boolean;
  icon: ReactNode;
  to: string;
};

export function NavItem({ children, collapsed, icon, to }: NavItemProps) {
  const link = (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(styles.root, isActive && styles.active, collapsed && styles.iconOnly)
      }
    >
      <span className={styles.icon} aria-hidden="true">
        {icon}
      </span>
      {collapsed ? null : <span>{children}</span>}
    </NavLink>
  );

  if (!collapsed) {
    return link;
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>{link}</TooltipTrigger>
      <TooltipContent>{children}</TooltipContent>
    </Tooltip>
  );
}
