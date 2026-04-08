"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import { createClient } from "@/lib/supabase";
import type { Provider } from "@supabase/supabase-js";

type Tab = "signin" | "signup" | "magic";

export default function SignInPage() {
  const router = useRouter();
  const { user } = useAppStore();
  const [tab, setTab] = useState<Tab>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Redirect if already logged in
  if (user.isLoggedIn) {
    router.push("/");
    return null;
  }

  const handleOAuth = async (provider: Provider) => {
    setError(null);
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin}/`,
      },
    });
    if (error) setError(error.message);
  };

  const handleEmailSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setError(null);
    setMessage(null);
    setLoading(true);

    const supabase = createClient();

    if (tab === "magic") {
      const { error } = await supabase.auth.signInWithOtp({ email });
      setLoading(false);
      if (error) {
        setError(error.message);
      } else {
        setMessage("Check your email for the magic link!");
      }
      return;
    }

    if (tab === "signup") {
      const { error } = await supabase.auth.signUp({ email, password });
      setLoading(false);
      if (error) {
        setError(error.message);
      } else {
        setMessage("Check your email to confirm your account!");
      }
      return;
    }

    // Sign in
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (error) {
      setError(error.message);
    }
    // onAuthStateChange in AuthProvider handles redirect
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top bar */}
      <header
        className="flex items-center justify-between px-4 py-2.5 border-b h-[49px]"
        style={{ background: "var(--bg-primary)", borderColor: "var(--border)" }}
      >
        <button
          onClick={() => router.push("/")}
          className="text-lg font-bold tracking-tight hover:opacity-80 transition-opacity"
          style={{ color: "var(--accent)" }}
        >
          Klare
        </button>
      </header>

      {/* Content */}
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          {/* Welcome text */}
          <div className="text-center mb-6">
            <h1 className="text-2xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>
              Welcome to <span style={{ color: "var(--accent)" }}>Klare.</span>
            </h1>
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              Sign in to save your progress and sync across devices
            </p>
          </div>

          {/* Card */}
          <div
            className="rounded-xl border p-6"
            style={{ background: "var(--bg-surface)", borderColor: "var(--border)" }}
          >
            {/* Tabs */}
            <div className="flex rounded-lg overflow-hidden border mb-6" style={{ borderColor: "var(--border)" }}>
              {(["signin", "signup", "magic"] as Tab[]).map((t) => (
                <button
                  key={t}
                  onClick={() => { setTab(t); setError(null); setMessage(null); }}
                  className="flex-1 py-2 text-sm font-medium transition-colors"
                  style={{
                    background: tab === t ? "var(--accent)" : "transparent",
                    color: tab === t ? "#fff" : "var(--text-secondary)",
                  }}
                >
                  {t === "signin" ? "Sign In" : t === "signup" ? "Sign Up" : "Magic Link"}
                </button>
              ))}
            </div>

            {/* Error / Success messages */}
            {error && (
              <div
                className="mb-4 px-3 py-2 rounded-lg text-sm"
                style={{ background: "rgba(255,68,68,0.1)", color: "#FF4444", border: "1px solid rgba(255,68,68,0.2)" }}
              >
                {error}
              </div>
            )}
            {message && (
              <div
                className="mb-4 px-3 py-2 rounded-lg text-sm"
                style={{ background: "rgba(34,197,94,0.1)", color: "#22C55E", border: "1px solid rgba(34,197,94,0.2)" }}
              >
                {message}
              </div>
            )}

            {/* OAuth buttons — hidden on Magic Link tab */}
            {tab !== "magic" && (
              <>
                <div className="space-y-2.5 mb-5">
                  <OAuthButton icon="G" label="Sign in with Google" onClick={() => handleOAuth("google")} />
                  <OAuthButton icon="M" label="Sign in with Microsoft" onClick={() => handleOAuth("azure")} />
                </div>

                <div className="flex items-center gap-3 mb-5">
                  <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                    Or continue with email
                  </span>
                  <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
                </div>
              </>
            )}

            {/* Email form */}
            <form onSubmit={handleEmailSignIn} className="space-y-4">
              <div>
                <label className="text-xs font-medium block mb-1.5" style={{ color: "var(--text-primary)" }}>
                  Email Address
                </label>
                <input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-lg border text-sm outline-none focus:border-[var(--accent)] transition-colors"
                  style={{
                    background: "var(--bg-elevated)",
                    borderColor: "var(--border)",
                    color: "var(--text-primary)",
                  }}
                />
              </div>

              {tab !== "magic" && (
                <div>
                  <label className="text-xs font-medium block mb-1.5" style={{ color: "var(--text-primary)" }}>
                    Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      placeholder="Enter your password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full px-3 py-2.5 rounded-lg border text-sm outline-none focus:border-[var(--accent)] transition-colors pr-10"
                      style={{
                        background: "var(--bg-elevated)",
                        borderColor: "var(--border)",
                        color: "var(--text-primary)",
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2"
                      style={{ color: "var(--text-muted)" }}
                    >
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M8 3C4.5 3 1.7 5.1.5 8c1.2 2.9 4 5 7.5 5s6.3-2.1 7.5-5c-1.2-2.9-4-5-7.5-5zm0 8.3A3.3 3.3 0 1 1 8 4.7a3.3 3.3 0 0 1 0 6.6zm0-5.3a2 2 0 1 0 0 4 2 2 0 0 0 0-4z" />
                      </svg>
                    </button>
                  </div>
                </div>
              )}

              {tab === "signin" && (
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={remember}
                    onChange={(e) => setRemember(e.target.checked)}
                    className="accent-[var(--accent)]"
                  />
                  <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
                    Remember me for 30 days
                  </span>
                </label>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50"
                style={{ background: "var(--accent)", color: "#fff" }}
              >
                {loading
                  ? "Please wait..."
                  : tab === "signin"
                    ? "Sign In"
                    : tab === "signup"
                      ? "Create Account"
                      : "Send Magic Link"}
              </button>
            </form>

            {tab === "signin" && (
              <p className="text-center mt-4">
                <button className="text-xs hover:underline" style={{ color: "var(--accent)" }}>
                  Forgot your password?
                </button>
              </p>
            )}
          </div>

          {/* Footer */}
          <p className="text-center text-xs mt-4" style={{ color: "var(--text-muted)" }}>
            By signing in, you agree to our Terms of Service and Privacy Policy
          </p>
        </div>
      </main>
    </div>
  );
}

function OAuthButton({
  icon,
  label,
  onClick,
}: {
  icon: string;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center justify-center gap-3 px-4 py-2.5 rounded-lg border text-sm font-medium hover:bg-[var(--bg-elevated)] transition-colors"
      style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}
    >
      <span className="w-5 h-5 flex items-center justify-center text-xs font-bold rounded"
        style={{
          background: icon === "G" ? "#4285F4" : "#00A4EF",
          color: "#fff",
        }}
      >
        {icon}
      </span>
      {label}
    </button>
  );
}
