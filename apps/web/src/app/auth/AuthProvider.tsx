import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { AuthSessionUser } from "@/services/auth/authApi";
import {
  authSessionQueryKey,
  useAuthSessionQuery,
  useLoginMutation,
  useLogoutMutation,
} from "@/services/auth/authQueries";
import { setUnauthorizedHandler } from "@/services/http/fetchJson";

type AuthContextValue = {
  enabled: boolean;
  user: AuthSessionUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isLoginPending: boolean;
  isLogoutPending: boolean;
  loginError: string | null;
  logoutError: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

type AuthProviderProps = {
  children: ReactNode;
};

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const queryClient = useQueryClient();
  const sessionQuery = useAuthSessionQuery();
  const loginMutation = useLoginMutation();
  const logoutMutation = useLogoutMutation();

  const session = sessionQuery.data;
  const enabled = session?.enabled ?? true;
  const user = session?.authenticated ? session.user : null;

  const handleLogin = useCallback(
    async (email: string, password: string) => {
      await loginMutation.mutateAsync({ email, password });
    },
    [loginMutation],
  );

  const handleLogout = useCallback(async () => {
    await logoutMutation.mutateAsync();
  }, [logoutMutation]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      queryClient.setQueryData(authSessionQueryKey, {
        enabled: true,
        authenticated: false,
        user: null,
      });
    });
    return () => setUnauthorizedHandler(null);
  }, [queryClient]);

  const value = useMemo<AuthContextValue>(
    () => ({
      enabled,
      user,
      isAuthenticated: user !== null,
      isLoading: sessionQuery.isPending,
      isLoginPending: loginMutation.isPending,
      isLogoutPending: logoutMutation.isPending,
      loginError: loginMutation.error
        ? errorMessage(loginMutation.error, "Login failed.")
        : null,
      logoutError: logoutMutation.error
        ? errorMessage(logoutMutation.error, "Logout failed.")
        : null,
      login: handleLogin,
      logout: handleLogout,
    }),
    [
      enabled,
      handleLogin,
      handleLogout,
      loginMutation.error,
      loginMutation.isPending,
      logoutMutation.error,
      logoutMutation.isPending,
      sessionQuery.isPending,
      user,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (value === null) {
    throw new Error("useAuth must be used within AuthProvider.");
  }
  return value;
}
