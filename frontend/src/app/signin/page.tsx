"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
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
    router.push("/upload");
    return null;
  }

  const handleOAuth = async (provider: Provider) => {
    setError(null);
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin}/upload`,
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
        toast.error(error.message);
      } else {
        setMessage("Check your email for the magic link!");
        toast.success("Magic link sent! Check your email.");
      }
      return;
    }

    if (tab === "signup") {
      const { error } = await supabase.auth.signUp({ email, password });
      setLoading(false);
      if (error) {
        setError(error.message);
        toast.error(error.message);
      } else {
        setMessage("Check your email to confirm your account!");
        toast.success("Account created! Check your email to confirm.");
      }
      return;
    }

    // Sign in
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (error) {
      setError(error.message);
      toast.error(error.message);
    } else {
      toast.success("Welcome back!");
    }
  };

  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden">
      {/* Background effects */}
      <div className="hero-glow hero-glow-pulse" />
      <div className="orb orb-orange" style={{ width: 300, height: 300, top: "10%", right: "-5%" }} />
      <div className="orb orb-purple" style={{ width: 250, height: 250, bottom: "10%", left: "-5%" }} />

      {/* Top bar */}
      <header
        className="relative z-10 flex items-center justify-between px-4 sm:px-6 py-2.5 h-[56px]"
        style={{
          background: "rgba(10, 10, 15, 0.7)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <button
          onClick={() => router.push("/")}
          className="text-lg font-bold tracking-tight hover:opacity-80 transition-opacity"
        >
          <span className="gradient-text">Klare</span>
        </button>
      </header>

      {/* Content */}
      <main className="relative z-10 flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md animate-fade-in-up">
          {/* Welcome text */}
          <div className="text-center mb-8">
            <h1 className="text-2xl sm:text-3xl font-bold mb-2" style={{ color: "var(--text-primary)" }}>
              Welcome to <span className="gradient-text">Klare</span>
            </h1>
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              Sign in to save your progress and sync across devices
            </p>
          </div>

          {/* Card */}
          <div className="glass rounded-2xl p-6 sm:p-8">
            {/* Tabs */}
            <div
              className="flex rounded-xl overflow-hidden mb-6 p-1"
              style={{ background: "var(--bg-elevated)" }}
            >
              {(["signin", "signup", "magic"] as Tab[]).map((t) => (
                <button
                  key={t}
                  onClick={() => { setTab(t); setError(null); setMessage(null); }}
                  className="flex-1 py-2 text-xs font-medium rounded-lg transition-all"
                  style={{
                    background: tab === t ? "linear-gradient(135deg, var(--accent), #FF8555)" : "transparent",
                    color: tab === t ? "#fff" : "var(--text-muted)",
                    boxShadow: tab === t ? "0 4px 12px var(--accent-glow)" : "none",
                  }}
                >
                  {t === "signin" ? "Sign In" : t === "signup" ? "Sign Up" : "Magic Link"}
                </button>
              ))}
            </div>

            {/* Error / Success messages */}
            {error && (
              <div
                className="mb-4 px-4 py-2.5 rounded-xl text-sm"
                style={{ background: "rgba(255,68,68,0.08)", color: "#FF6666", border: "1px solid rgba(255,68,68,0.15)" }}
              >
                {error}
              </div>
            )}
            {message && (
              <div
                className="mb-4 px-4 py-2.5 rounded-xl text-sm"
                style={{ background: "rgba(34,197,94,0.08)", color: "#4ade80", border: "1px solid rgba(34,197,94,0.15)" }}
              >
                {message}
              </div>
            )}

            {/* OAuth buttons */}
            {tab !== "magic" && (
              <>
                <div className="space-y-2.5 mb-5">
                  <OAuthButton
                    icon={
                      <svg width="16" height="16" viewBox="0 0 24 24">
                        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
                        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                      </svg>
                    }
                    label="Continue with Google"
                    onClick={() => handleOAuth("google")}
                  />
                  <OAuthButton
                    icon={
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="#00A4EF">
                        <path d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zM24 11.4H12.6V0H24v11.4z" />
                      </svg>
                    }
                    label="Continue with Microsoft"
                    onClick={() => handleOAuth("azure")}
                  />
                </div>

                <div className="flex items-center gap-3 mb-5">
                  <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                    or continue with email
                  </span>
                  <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
                </div>
              </>
            )}

            {/* Email form */}
            <form onSubmit={handleEmailSignIn} className="space-y-4">
              <div>
                <label className="text-xs font-medium block mb-1.5" style={{ color: "var(--text-secondary)" }}>
                  Email
                </label>
                <input
                  type="email"
                  placeholder="you@university.edu"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl text-sm outline-none transition-all"
                  style={{
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border)",
                    color: "var(--text-primary)",
                  }}
                  onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
                  onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
                />
              </div>

              {tab !== "magic" && (
                <div>
                  <label className="text-xs font-medium block mb-1.5" style={{ color: "var(--text-secondary)" }}>
                    Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      placeholder="Enter your password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-xl text-sm outline-none transition-all pr-10"
                      style={{
                        background: "var(--bg-elevated)",
                        border: "1px solid var(--border)",
                        color: "var(--text-primary)",
                      }}
                      onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
                      onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-1"
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
                className="btn-glow w-full py-3 rounded-xl text-sm font-semibold transition-all disabled:opacity-50"
                style={{
                  background: "linear-gradient(135deg, var(--accent), #FF8555)",
                  color: "#fff",
                  boxShadow: "0 8px 32px var(--accent-glow)",
                }}
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
                <button
                  onClick={async () => {
                    if (!email) {
                      toast.error("Enter your email first");
                      return;
                    }
                    setLoading(true);
                    const supabase = createClient();
                    const { error } = await supabase.auth.resetPasswordForEmail(email, {
                      redirectTo: `${window.location.origin}/signin`,
                    });
                    setLoading(false);
                    if (error) {
                      toast.error(error.message);
                    } else {
                      toast.success("Password reset email sent! Check your inbox.");
                    }
                  }}
                  className="text-xs transition-colors"
                  style={{ color: "var(--accent)" }}
                >
                  Forgot your password?
                </button>
              </p>
            )}
          </div>

          {/* Footer */}
          <p className="text-center text-xs mt-6" style={{ color: "var(--text-muted)" }}>
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
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center justify-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all"
      style={{
        background: "var(--bg-elevated)",
        border: "1px solid var(--border)",
        color: "var(--text-primary)",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "rgba(255, 255, 255, 0.08)";
        e.currentTarget.style.borderColor = "var(--border-hover)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "var(--bg-elevated)";
        e.currentTarget.style.borderColor = "var(--border)";
      }}
    >
      {icon}
      {label}
    </button>
  );
}
