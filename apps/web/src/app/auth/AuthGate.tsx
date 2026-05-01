import type { ReactNode } from "react";
import { useAuth } from "@/app/auth/AuthProvider";
import { LoginDialog } from "@/app/auth/LoginDialog";
import styles from "./AuthGate.module.css";

type AuthGateProps = {
  children: ReactNode;
};

export function AuthGate({ children }: AuthGateProps) {
  const auth = useAuth();

  if (auth.isLoading) {
    return <div className={styles.loading}>Checking session...</div>;
  }

  if (!auth.enabled || auth.isAuthenticated) {
    return children;
  }

  return (
    <>
      {children}
      <LoginDialog
        error={auth.loginError}
        onLogin={auth.login}
        open
        submitting={auth.isLoginPending}
      />
    </>
  );
}
