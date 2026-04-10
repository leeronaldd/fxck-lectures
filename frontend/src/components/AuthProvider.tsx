"use client";

import { useEffect } from "react";
import { createClient } from "@/lib/supabase";
import { useAppStore } from "@/lib/store";
import { updateProfile } from "@/lib/api";

/** Save quiz answers from localStorage to backend after sign-in */
async function syncQuizToProfile() {
  try {
    const saved = localStorage.getItem("klare_quiz");
    if (!saved) return;

    const answers = JSON.parse(saved) as { question: string; answer: string }[];
    const profile: Record<string, string> = {};

    for (const a of answers) {
      if (a.question.includes("studying")) profile.study_program = a.answer;
      if (a.question.includes("year")) profile.study_year = a.answer;
      if (a.question.includes("frustrates")) profile.frustration = a.answer;
      if (a.question.includes("hear")) profile.referral_source = a.answer;
    }

    if (Object.keys(profile).length > 0) {
      await updateProfile(profile);
      localStorage.removeItem("klare_quiz"); // Synced — clear local
    }
  } catch {}
}

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
        syncQuizToProfile();
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
        if (_event === "SIGNED_IN") {
          syncQuizToProfile();
        }
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
