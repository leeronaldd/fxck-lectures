"use client";

import { useEffect } from "react";
import { createClient } from "@/lib/supabase";
import { useAppStore } from "@/lib/store";
import { updateProfile } from "@/lib/api";
import { identifyUser, resetUser, trackEvent, initAnalytics } from "@/lib/analytics";

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
    // Boot PostHog immediately so anonymous pageviews land in analytics.
    // Previously boot() only ran when a trackEvent fired, which meant
    // landing-page visitors were invisible to PostHog funnels.
    initAnalytics();

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
        identifyUser(u.id, { email: u.email });
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
        identifyUser(u.id, { email: u.email });
        loadSessions();
        if (_event === "SIGNED_IN") {
          // Distinguish first-time signup from returning login: if created_at
          // and last_sign_in_at match (or are within a few seconds), it's a
          // brand-new account.
          const created = u.created_at ? new Date(u.created_at).getTime() : 0;
          const lastSignIn = u.last_sign_in_at ? new Date(u.last_sign_in_at).getTime() : 0;
          const isNewSignup = created && lastSignIn && Math.abs(lastSignIn - created) < 5000;
          trackEvent(isNewSignup ? "signup_complete" : "login", {
            provider: u.app_metadata?.provider,
          });
          syncQuizToProfile();
        }
      } else {
        clearUser();
        resetUser();
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setUser, clearUser, setAuthLoading]);

  return <>{children}</>;
}
