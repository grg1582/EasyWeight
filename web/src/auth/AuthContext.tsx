import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import * as client from "../api/client";
import { useMe } from "../api/queries";
import type { User } from "../api/types";

type Status = "loading" | "signedIn" | "signedOut" | "offline";

interface Auth {
  status: Status;
  user: User | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  retry: () => void;
}

const AuthContext = createContext<Auth | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  // Is there a session to check? (a refresh token from an earlier visit)
  const [session, setSession] = useState(client.hasSession);
  const me = useMe(session);

  useEffect(
    () =>
      client.onSignedOut(() => {
        setSession(false);
        queryClient.clear();
      }),
    [queryClient],
  );

  const start = useCallback(() => {
    queryClient.clear(); // nothing from a previous user stays cached
    setSession(true);
  }, [queryClient]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      await client.login(email, password);
      start();
    },
    [start],
  );

  const signUp = useCallback(
    async (email: string, password: string) => {
      await client.register(email, password);
      start();
    },
    [start],
  );

  const signOut = useCallback(async () => {
    await client.logout();
    setSession(false);
    queryClient.clear();
  }, [queryClient]);

  let status: Status;
  if (!session) status = "signedOut";
  else if (me.data) status = "signedIn";
  else if (me.isError) status = client.hasSession() ? "offline" : "signedOut";
  else status = "loading";

  const value = useMemo(
    () => ({
      status,
      user: me.data ?? null,
      signIn,
      signUp,
      signOut,
      retry: () => void me.refetch(),
    }),
    [status, me, signIn, signUp, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): Auth {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("useAuth must be used inside <AuthProvider>");
  return auth;
}
