import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { me, refresh } from "../api/authApi";
import { ApiError } from "../api/client";
import type { UserSummary } from "../types/api";

type AuthState = {
  user: UserSummary | null;
  ready: boolean;
  setUser: (next: UserSummary | null) => void;
  reloadUser: () => Promise<UserSummary | null>;
};

const AuthContext = createContext<AuthState | undefined>(undefined);

async function resolveUser(): Promise<UserSummary | null> {
  try {
    return await me();
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      try {
        await refresh();
        return await me();
      } catch {
        return null;
      }
    }
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserSummary | null>(null);
  const [ready, setReady] = useState(false);

  const reloadUser = useCallback(async () => {
    const current = await resolveUser();
    setUser(current);
    return current;
  }, []);

  useEffect(() => {
    let ignore = false;
    resolveUser()
      .then((current) => {
        if (!ignore) {
          setUser(current);
        }
      })
      .finally(() => {
        if (!ignore) {
          setReady(true);
        }
      });

    return () => {
      ignore = true;
    };
  }, []);

  const value = useMemo(
    () => ({
      user,
      ready,
      setUser,
      reloadUser,
    }),
    [user, ready, reloadUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
