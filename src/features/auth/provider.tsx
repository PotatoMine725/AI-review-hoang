"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getSupabase } from "@/lib/supabase/client";
import { accountFromUser, normalizeEmail, validateRegistration, type Account } from "./model";

type Auth = {
  account: Account | null; ready: boolean; error: boolean;
  signIn: (email: string, password: string) => Promise<Account>;
  signUp: (name: string, email: string, password: string, confirmation: string) => Promise<Account>;
  signOut: () => Promise<void>;
};
const Context = createContext<Auth | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<Account | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) { Promise.resolve().then(() => { setError(true); setReady(true); }); return; }
    let alive = true;
    supabase.auth.getSession()
      .then(({ data }) => { if (alive) setAccount(data.session ? accountFromUser(data.session.user) : null); })
      .catch(() => { if (alive) setError(true); })
      .finally(() => { if (alive) setReady(true); });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (alive) setAccount(session ? accountFromUser(session.user) : null);
    });
    return () => { alive = false; subscription.unsubscribe(); };
  }, []);

  function client() {
    const supabase = getSupabase();
    if (!supabase || error) throw new Error("config");
    return supabase;
  }
  async function signIn(email: string, password: string) {
    const { data, error: failure } = await client().auth.signInWithPassword({ email: normalizeEmail(email), password });
    if (failure || !data.user) throw new Error(failure?.code === "invalid_credentials" || failure?.status === 400 ? "credentials" : "network");
    const next = accountFromUser(data.user);
    setAccount(next);
    return next;
  }
  async function signUp(name: string, email: string, password: string, confirmation: string) {
    validateRegistration(name, email, password, confirmation);
    const { data, error: failure } = await client().auth.signUp({ email: normalizeEmail(email), password, options: { data: { name: name.trim() } } });
    if (failure) throw new Error(failure.code === "user_already_exists" ? "duplicate" : "network");
    // Supabase giả lập "email đã tồn tại" bằng user không có identity khi bật xác nhận email.
    if (data.user && data.user.identities?.length === 0) throw new Error("duplicate");
    if (!data.session || !data.user) throw new Error("confirm");
    const next = accountFromUser(data.user);
    setAccount(next);
    return next;
  }
  async function signOut() {
    await getSupabase()?.auth.signOut();
    setAccount(null);
  }
  return <Context.Provider value={{ account, ready, error, signIn, signUp, signOut }}>{children}</Context.Provider>;
}

export function useAuth() {
  const auth = useContext(Context);
  if (!auth) throw new Error("AuthProvider required");
  return auth;
}
