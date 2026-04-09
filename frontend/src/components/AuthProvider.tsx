"use client";

import { useEffect } from "react";
import { createClient } from "@/lib/supabase";
import { useAppStore } from "@/lib/store";

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const { setUser, clearUser, setAuthLoading, loadSessions } = useAppStore();

  useEffect(() => {
    const supabase = createClient();

    // Check for existing session on mount
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        const u = session.user;
        setUser({
          isLoggedIn: true,
          id: u.id,
          name: u.user_metadata?.full_name || u.email?.split("@")[0] || "User",
          email: u.email || "",
          avatar: u.user_metadata?.avatar_url || null,
        });
        loadSessions();
      }
      setAuthLoading(false);
    });

    // Listen for auth state changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        const u = session.user;
        setUser({
          isLoggedIn: true,
          id: u.id,
          name: u.user_metadata?.full_name || u.email?.split("@")[0] || "User",
          email: u.email || "",
          avatar: u.user_metadata?.avatar_url || null,
        });
        loadSessions();
      } else {
        clearUser();
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setUser, clearUser, setAuthLoading]);

  return <>{children}</>;
}
