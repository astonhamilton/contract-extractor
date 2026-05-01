import { useEffect, useId, useState, type FormEvent } from "react";
import { Button } from "@/ui/primitives/Button/Button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/ui/primitives/Dialog/Dialog";
import { TextField } from "@/ui/primitives/TextField/TextField";
import styles from "./LoginDialog.module.css";

type LoginDialogProps = {
  open: boolean;
  error: string | null;
  submitting: boolean;
  onLogin: (email: string, password: string) => Promise<void>;
};

export function LoginDialog({
  open,
  error,
  submitting,
  onLogin,
}: LoginDialogProps) {
  const emailId = useId();
  const passwordId = useId();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [editedAfterServerError, setEditedAfterServerError] = useState(false);

  useEffect(() => {
    setEditedAfterServerError(false);
  }, [error]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedEmail = email.trim();
    if (!trimmedEmail || !password) {
      setLocalError("Enter your email and password.");
      return;
    }
    setLocalError(null);
    setEditedAfterServerError(false);
    await onLogin(trimmedEmail, password);
  }

  const displayedError = localError ?? (editedAfterServerError ? null : error);

  return (
    <Dialog open={open} modal>
      <DialogContent
        aria-describedby="auth-login-description"
        onEscapeKeyDown={(event) => event.preventDefault()}
        onInteractOutside={(event) => event.preventDefault()}
      >
        <div className={styles.header}>
          <p className={styles.kicker}>Authentication required</p>
          <DialogTitle className={styles.title}>Sign in to continue</DialogTitle>
          <DialogDescription
            className={styles.copy}
            id="auth-login-description"
          >
            Enter your workspace credentials to access contract intelligence.
          </DialogDescription>
        </div>
        <form className={styles.form} onSubmit={handleSubmit}>
          {displayedError ? <p className={styles.error}>{displayedError}</p> : null}
          <label className={styles.field} htmlFor={emailId}>
            <span className={styles.label}>Email</span>
            <TextField
              autoComplete="email"
              autoFocus
              className={styles.input}
              id={emailId}
              onChange={(event) => {
                setEmail(event.target.value);
                setLocalError(null);
                setEditedAfterServerError(true);
              }}
              type="email"
              value={email}
            />
          </label>
          <label className={styles.field} htmlFor={passwordId}>
            <span className={styles.label}>Password</span>
            <TextField
              autoComplete="current-password"
              className={styles.input}
              id={passwordId}
              onChange={(event) => {
                setPassword(event.target.value);
                setLocalError(null);
                setEditedAfterServerError(true);
              }}
              type="password"
              value={password}
            />
          </label>
          <div className={styles.actions}>
            <Button disabled={submitting} type="submit" variant="primary">
              {submitting ? "Signing in..." : "Sign in"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
