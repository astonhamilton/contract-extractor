import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getAuthSession,
  login,
  logout,
  type AuthLoginResponse,
  type AuthSessionResponse,
} from "@/services/auth/authApi";
import { corpusKeys } from "@/services/corpus/corpusQueries";

export const authSessionQueryKey = ["auth", "session"] as const;

export function useAuthSessionQuery() {
  return useQuery({
    queryKey: authSessionQueryKey,
    queryFn: ({ signal }) => getAuthSession(signal),
    retry: false,
    staleTime: 30_000,
  });
}

export function useLoginMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      login(email, password),
    onSuccess: (response: AuthLoginResponse) => {
      queryClient.setQueryData<AuthSessionResponse>(authSessionQueryKey, {
        enabled: true,
        authenticated: response.authenticated,
        user: response.user,
      });
      void queryClient.invalidateQueries({ queryKey: corpusKeys.all });
    },
  });
}

export function useLogoutMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.setQueryData<AuthSessionResponse>(authSessionQueryKey, {
        enabled: true,
        authenticated: false,
        user: null,
      });
      void queryClient.invalidateQueries();
    },
  });
}
