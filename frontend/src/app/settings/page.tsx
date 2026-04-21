"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { useAppStore } from "@/lib/store";

const AVATAR_COLORS = [
  "#FF6B35", "#EF4444", "#F59E0B", "#22C55E",
  "#3B82F6", "#8B5CF6", "#EC4899", "#6B7280",
];

const TABS = ["Account", "Billing", "Usage", "Privacy", "Customization"];

export default function SettingsPage() {
  return (
    <Suspense>
      <SettingsContent />
    </Suspense>
  );
}

function SettingsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAppStore();
  const [activeTab, setActiveTab] = useState("Account");

  // Set initial tab from URL param on mount only
  useEffect(() => {
    const tab = searchParams.get("tab");
    if (tab && TABS.includes(tab)) {
      setActiveTab(tab);
      if (tab === "Billing") setShowPlanSelector(true);
    }
    // Stripe's success_url appends ?upgraded=true — convert it into a
    // checkout_complete analytics event so we can measure conversion.
    if (searchParams.get("upgraded") === "true") {
      import("@/lib/analytics").then(({ trackEvent }) =>
        trackEvent("checkout_complete")
      );
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const [displayName, setDisplayName] = useState(user.name || "");
  const [avatarColor, setAvatarColor] = useState("#FF6B35");
  const [billingPeriod, setBillingPeriod] = useState<"yearly" | "monthly">("yearly");
  const [showPlanSelector, setShowPlanSelector] = useState(false);

  // Quiz customization state
  const [studyProgram, setStudyProgram] = useState("");
  const [studyYear, setStudyYear] = useState("");

  // Usage info (live from backend)
  const [usage, setUsage] = useState<{ used: number; limit: number; tier: string; period_end: string | null } | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const { fetchUsage } = await import("@/lib/api");
        const u = await fetchUsage();
        if (u) setUsage(u);
      } catch {}
    })();
  }, []);

  // Load profile from backend (falls back to localStorage)
  useEffect(() => {
    (async () => {
      try {
        const { fetchProfile } = await import("@/lib/api");
        const profile = await fetchProfile();
        if (profile) {
          if (profile.display_name) setDisplayName(profile.display_name);
          if (profile.avatar_color) setAvatarColor(profile.avatar_color);
          if (profile.study_program) setStudyProgram(profile.study_program);
          if (profile.study_year) setStudyYear(profile.study_year);
          return;
        }
      } catch {}
      // Fallback to localStorage
      try {
        const saved = localStorage.getItem("klare_quiz");
        if (saved) {
          const answers = JSON.parse(saved);
          for (const a of answers) {
            if (a.question.includes("studying")) setStudyProgram(a.answer);
            if (a.question.includes("year")) setStudyYear(a.answer);
          }
        }
      } catch {}
    })();
  }, []);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
            Settings
          </h1>
          <button
            onClick={() => router.back()}
            className="text-sm px-3 py-1.5 rounded-lg transition-colors"
            style={{ color: "var(--text-muted)" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-primary)")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-muted)")}
          >
            Done
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-8 overflow-x-auto pb-1">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className="px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap"
              style={{
                background: activeTab === tab ? "var(--accent-dim)" : "transparent",
                color: activeTab === tab ? "var(--accent)" : "var(--text-muted)",
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === "Account" && (
          <div className="space-y-6">
            {/* Avatar */}
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-3" style={{ color: "var(--text-secondary)" }}>
                Profile
              </label>
              <div className="flex items-center gap-4 mb-4">
                <div
                  className="w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold text-white shrink-0"
                  style={{ background: avatarColor }}
                >
                  {(displayName || user.name || "?").charAt(0).toUpperCase()}
                </div>
                <div className="flex gap-2 flex-wrap">
                  {AVATAR_COLORS.map((color) => (
                    <button
                      key={color}
                      onClick={() => setAvatarColor(color)}
                      className="w-7 h-7 rounded-full transition-transform"
                      style={{
                        background: color,
                        transform: avatarColor === color ? "scale(1.2)" : "scale(1)",
                        boxShadow: avatarColor === color ? `0 0 0 2px var(--bg-base), 0 0 0 4px ${color}` : "none",
                      }}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* Name */}
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: "var(--text-secondary)" }}>
                Display Name
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Your name"
                className="w-full px-4 py-3 rounded-xl text-sm outline-none"
                style={{
                  background: "var(--bg-elevated)",
                  border: "1px solid var(--border)",
                  color: "var(--text-primary)",
                }}
              />
            </div>

            {/* Email (read-only) */}
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: "var(--text-secondary)" }}>
                Email
              </label>
              <div
                className="px-4 py-3 rounded-xl text-sm"
                style={{
                  background: "var(--bg-elevated)",
                  border: "1px solid var(--border)",
                  color: "var(--text-muted)",
                }}
              >
                {user.email || "Not signed in"}
              </div>
            </div>

            {/* Save */}
            <button
              onClick={async () => {
                const { updateProfile } = await import("@/lib/api");
                const ok = await updateProfile({ display_name: displayName, avatar_color: avatarColor });
                if (ok) toast("Profile updated!");
                else toast("Failed to save. Try again.");
              }}
              className="px-6 py-2.5 rounded-xl text-sm font-medium"
              style={{
                background: "var(--accent)",
                color: "#fff",
              }}
            >
              Save Changes
            </button>
          </div>
        )}

        {activeTab === "Billing" && (
          <div className="space-y-6">
            {/* Current plan */}
            <div
              className="p-5 rounded-xl"
              style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  Current Plan
                </span>
                <span
                  className="text-xs px-2.5 py-1 rounded-full font-medium capitalize"
                  style={{ background: "var(--accent-dim)", color: "var(--accent)" }}
                >
                  {usage?.tier || "Free"}
                </span>
              </div>
              <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>
                {usage?.limit === -1
                  ? "Unlimited lectures"
                  : `${usage?.limit ?? 2} lectures per month`}
              </p>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setShowPlanSelector(!showPlanSelector)}
                  className="text-sm font-medium"
                  style={{ color: "var(--accent)" }}
                >
                  {showPlanSelector ? "Hide plans" : (usage?.tier && usage.tier !== "free" ? "Change Plan" : "Adjust Plan")}
                </button>
                {usage?.tier && usage.tier !== "free" && usage.tier !== "unlimited" && (
                  <button
                    onClick={async () => {
                      const { openBillingPortal } = await import("@/lib/api");
                      const url = await openBillingPortal();
                      if (url) {
                        window.location.href = url;
                      } else {
                        toast("Could not open billing portal. Please try again.");
                      }
                    }}
                    className="text-sm font-medium"
                    style={{ color: "var(--text-muted)" }}
                  >
                    Manage Subscription
                  </button>
                )}
              </div>
            </div>

            {/* Plan selector */}
            {showPlanSelector && (
              <div>
                {/* Period toggle */}
                <div className="flex flex-col items-center justify-center mb-6 gap-2">
                  <div className="inline-grid grid-cols-2 rounded-lg p-0.5 w-64" style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}>
                    <button
                      onClick={() => setBillingPeriod("monthly")}
                      className="px-4 py-2 rounded-md text-sm font-medium transition-all text-center"
                      style={{
                        background: billingPeriod === "monthly" ? "var(--accent)" : "transparent",
                        color: billingPeriod === "monthly" ? "#fff" : "var(--text-muted)",
                      }}
                    >
                      Monthly
                    </button>
                    <button
                      onClick={() => setBillingPeriod("yearly")}
                      className="px-4 py-2 rounded-md text-sm font-medium transition-all text-center"
                      style={{
                        background: billingPeriod === "yearly" ? "var(--accent)" : "transparent",
                        color: billingPeriod === "yearly" ? "#fff" : "var(--text-muted)",
                      }}
                    >
                      Yearly
                    </button>
                  </div>
                  <p className="text-[11px]" style={{ color: "var(--text-muted)" }}>
                    All prices in AUD. Cancel anytime.
                  </p>
                </div>

                {/* Plan cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Free */}
                  <div
                    className="p-5 rounded-xl flex flex-col"
                    style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}
                  >
                    <h3 className="text-lg font-bold mb-1" style={{ color: "var(--text-primary)" }}>Free</h3>
                    <p className="text-2xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>
                      $0<span className="text-sm font-normal" style={{ color: "var(--text-muted)" }}>&nbsp;</span>
                    </p>
                    <div className="mb-3" style={{ height: "1rem" }} />
                    <ul className="space-y-2 mb-5 text-sm flex-1" style={{ color: "var(--text-secondary)" }}>
                      <li className="flex items-center gap-2">
                        <span style={{ color: "var(--accent)" }}>&#10003;</span> 2 free lectures
                      </li>
                      <li className="flex items-center gap-2">
                        <span style={{ color: "var(--accent)" }}>&#10003;</span> AI-powered explanations
                      </li>
                      <li className="flex items-center gap-2">
                        <span style={{ color: "var(--accent)" }}>&#10003;</span> Textbook fact-checking
                      </li>
                    </ul>
                    <button
                      className="w-full py-2.5 rounded-xl text-sm font-medium mt-auto"
                      style={{ background: "var(--bg-base)", border: "1px solid var(--border)", color: "var(--text-muted)" }}
                      disabled
                    >
                      Current Plan
                    </button>
                  </div>

                  {/* Pro */}
                  <div
                    className="p-5 rounded-xl relative flex flex-col"
                    style={{ background: "var(--bg-elevated)", border: "1px solid rgba(255, 107, 53, 0.3)" }}
                  >
                    <div
                      className="absolute -top-3 left-1/2 -translate-x-1/2 text-[10px] px-3 py-0.5 rounded-full font-semibold"
                      style={{ background: "var(--accent)", color: "#fff" }}
                    >
                      POPULAR
                    </div>
                    <h3 className="text-lg font-bold mb-1" style={{ color: "var(--text-primary)" }}>Pro</h3>
                    <p className="text-2xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>
                      {billingPeriod === "yearly" ? "$5.83" : "$12.99"}
                      <span className="text-sm font-normal" style={{ color: "var(--text-muted)" }}>
                        {" "}AUD/mo
                      </span>
                    </p>
                    <p className="text-xs mb-3" style={{ color: "var(--text-muted)", minHeight: "1rem" }}>
                      {billingPeriod === "yearly" ? (
                        <>Billed as $69.99/yr — <span style={{ color: "#22C55E" }}>save 55%</span></>
                      ) : (
                        <>&nbsp;</>
                      )}
                    </p>
                    <ul className="space-y-2 mb-5 text-sm flex-1" style={{ color: "var(--text-secondary)" }}>
                      <li className="flex items-center gap-2">
                        <span style={{ color: "var(--accent)" }}>&#10003;</span> 15 lectures per month
                      </li>
                      <li className="flex items-center gap-2">
                        <span style={{ color: "var(--accent)" }}>&#10003;</span> 5 lectures per day
                      </li>
                      <li className="flex items-center gap-2">
                        <span style={{ color: "var(--accent)" }}>&#10003;</span> Priority processing
                      </li>
                      <li className="flex items-center gap-2">
                        <span style={{ color: "var(--accent)" }}>&#10003;</span> Personalized learning profile
                      </li>
                    </ul>
                    <button
                      onClick={async () => {
                        const { trackEvent } = await import("@/lib/analytics");
                        const isPaid = usage?.tier && usage.tier !== "free" && usage.tier !== "unlimited";
                        // Existing subscribers must go through the Customer
                        // Portal so Stripe can prorate the plan change.
                        // Otherwise we'd create a duplicate subscription.
                        if (isPaid) {
                          trackEvent("plan_change_start", { from: usage?.tier, to: "pro", period: billingPeriod });
                          const { openBillingPortal } = await import("@/lib/api");
                          const url = await openBillingPortal();
                          if (url) window.location.href = url;
                          else toast("Could not open billing portal. Please try again.");
                          return;
                        }
                        trackEvent("checkout_start", { tier: "pro", period: billingPeriod });
                        const { createCheckoutSession } = await import("@/lib/api");
                        const url = await createCheckoutSession(billingPeriod, "pro");
                        if (url) {
                          window.location.href = url;
                        } else {
                          toast("Something went wrong. Please try again.");
                        }
                      }}
                      className="w-full py-2.5 rounded-xl text-sm font-semibold mt-auto"
                      style={{
                        background: "linear-gradient(135deg, var(--accent), #FF8555)",
                        color: "#fff",
                      }}
                    >
                      {usage?.tier === "pro"
                        ? (billingPeriod === "yearly" ? "Switch to Pro Yearly" : "Current Plan")
                        : usage?.tier === "max"
                          ? "Downgrade to Pro"
                          : "Upgrade to Pro"}
                    </button>
                  </div>

                  {/* Max */}
                  <div
                    className="p-5 rounded-xl relative flex flex-col"
                    style={{ background: "var(--bg-elevated)", border: "1px solid rgba(255, 107, 53, 0.3)" }}
                  >
                    <h3 className="text-lg font-bold mb-1" style={{ color: "var(--text-primary)" }}>Max</h3>
                    <p className="text-2xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>
                      {billingPeriod === "yearly" ? "$13.33" : "$29.99"}
                      <span className="text-sm font-normal" style={{ color: "var(--text-muted)" }}>
                        {" "}AUD/mo
                      </span>
                    </p>
                    <p className="text-xs mb-3" style={{ color: "var(--text-muted)", minHeight: "1rem" }}>
                      {billingPeriod === "yearly" ? (
                        <>Billed as $159.99/yr — <span style={{ color: "#22C55E" }}>save 55%</span></>
                      ) : (
                        <>&nbsp;</>
                      )}
                    </p>
                    <ul className="space-y-2 mb-5 text-sm flex-1" style={{ color: "var(--text-secondary)" }}>
                      <li className="flex items-center gap-2">
                        <span style={{ color: "var(--accent)" }}>&#10003;</span> 50 lectures per month
                      </li>
                      <li className="flex items-center gap-2">
                        <span style={{ color: "var(--accent)" }}>&#10003;</span> 10 lectures per day
                      </li>
                      <li className="flex items-center gap-2">
                        <span style={{ color: "var(--accent)" }}>&#10003;</span> Priority processing
                      </li>
                      <li className="flex items-center gap-2">
                        <span style={{ color: "var(--accent)" }}>&#10003;</span> Built for power users
                      </li>
                    </ul>
                    <button
                      onClick={async () => {
                        const { trackEvent } = await import("@/lib/analytics");
                        const isPaid = usage?.tier && usage.tier !== "free" && usage.tier !== "unlimited";
                        if (isPaid) {
                          trackEvent("plan_change_start", { from: usage?.tier, to: "max", period: billingPeriod });
                          const { openBillingPortal } = await import("@/lib/api");
                          const url = await openBillingPortal();
                          if (url) window.location.href = url;
                          else toast("Could not open billing portal. Please try again.");
                          return;
                        }
                        trackEvent("checkout_start", { tier: "max", period: billingPeriod });
                        const { createCheckoutSession } = await import("@/lib/api");
                        const url = await createCheckoutSession(billingPeriod, "max");
                        if (url) {
                          window.location.href = url;
                        } else {
                          toast("Something went wrong. Please try again.");
                        }
                      }}
                      className="w-full py-2.5 rounded-xl text-sm font-semibold mt-auto"
                      style={{
                        background: "linear-gradient(135deg, var(--accent), #FF8555)",
                        color: "#fff",
                      }}
                    >
                      {usage?.tier === "max"
                        ? (billingPeriod === "yearly" ? "Switch to Max Yearly" : "Current Plan")
                        : "Upgrade to Max"}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "Usage" && (
          <div className="space-y-6">
            {/* Usage bar — live */}
            <div
              className="p-5 rounded-xl"
              style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  Lectures used
                </span>
                <span className="text-sm font-bold" style={{ color: "var(--accent)" }}>
                  {usage === null
                    ? "…"
                    : usage.limit === -1
                      ? `${usage.used} / ∞`
                      : `${usage.used} / ${usage.limit}`}
                </span>
              </div>
              <div className="h-2 rounded-full" style={{ background: "var(--bg-base)" }}>
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width:
                      usage === null
                        ? "0%"
                        : usage.limit === -1
                          ? "100%"
                          : `${Math.min(100, Math.round((usage.used / Math.max(1, usage.limit)) * 100))}%`,
                    background:
                      usage && usage.limit !== -1 && usage.used >= usage.limit
                        ? "#FF4444"
                        : "var(--accent)",
                  }}
                />
              </div>
              <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>
                {usage?.tier === "unlimited"
                  ? "Unlimited plan — go wild."
                  : usage?.tier === "pro"
                    ? `Pro plan: ${usage.limit} lectures this billing period${usage?.period_end ? ` · renews ${new Date(usage.period_end).toLocaleDateString()}` : ""}`
                    : usage?.tier === "max"
                      ? `Max plan: ${usage.limit} lectures this billing period${usage?.period_end ? ` · renews ${new Date(usage.period_end).toLocaleDateString()}` : ""}`
                      : `Free plan includes ${usage?.limit ?? 2} lifetime lectures`}
              </p>
            </div>

            {/* Usage history placeholder */}
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-3" style={{ color: "var(--text-secondary)" }}>
                Recent Activity
              </label>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                Usage history will appear here after you process lectures.
              </p>
            </div>
          </div>
        )}

        {activeTab === "Privacy" && (
          <div className="space-y-6">
            <div
              className="p-5 rounded-xl"
              style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}
            >
              <h3 className="text-sm font-medium mb-2" style={{ color: "var(--text-primary)" }}>
                Your Data
              </h3>
              <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>
                We store your lecture transcripts and generated documents to provide the service.
                Your data is never shared with third parties or used for training.
                Lecture content is processed via Google Vertex AI and deleted from their servers after processing.
              </p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => toast("Data export coming soon!")}
                className="px-4 py-2.5 rounded-xl text-sm font-medium"
                style={{
                  background: "var(--bg-elevated)",
                  border: "1px solid var(--border)",
                  color: "var(--text-primary)",
                }}
              >
                Download My Data
              </button>
              <button
                onClick={() => toast("Contact support@klare.ai to delete your account.")}
                className="px-4 py-2.5 rounded-xl text-sm font-medium"
                style={{
                  background: "rgba(239, 68, 68, 0.1)",
                  border: "1px solid rgba(239, 68, 68, 0.2)",
                  color: "#ef4444",
                }}
              >
                Delete All My Data
              </button>
            </div>
          </div>
        )}

        {activeTab === "Customization" && (
          <div className="space-y-6">
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              These settings personalize your lecture outputs. Change them anytime.
            </p>

            {/* Study program */}
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: "var(--text-secondary)" }}>
                What are you studying?
              </label>
              <select
                value={studyProgram}
                onChange={(e) => setStudyProgram(e.target.value)}
                className="w-full px-4 py-3 rounded-xl text-sm outline-none"
                style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
              >
                <option value="">Select...</option>
                <option>Medicine / Biomedical Science</option>
                <option>Nursing / Midwifery</option>
                <option>Pharmacy</option>
                <option>Dentistry</option>
                <option>Other health science</option>
              </select>
            </div>

            {/* Year */}
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-2" style={{ color: "var(--text-secondary)" }}>
                What year are you in?
              </label>
              <div className="flex gap-2">
                {["1st year", "2nd year", "3rd year", "4th year+"].map((yr) => (
                  <button
                    key={yr}
                    onClick={() => setStudyYear(yr)}
                    className="flex-1 px-3 py-2.5 rounded-xl text-sm font-medium transition-all"
                    style={{
                      background: studyYear === yr ? "var(--accent-dim)" : "var(--bg-elevated)",
                      border: studyYear === yr ? "1px solid rgba(255,107,53,0.4)" : "1px solid var(--border)",
                      color: studyYear === yr ? "var(--accent)" : "var(--text-primary)",
                    }}
                  >
                    {yr}
                  </button>
                ))}
              </div>
            </div>

            {/* Save */}
            <button
              onClick={async () => {
                const { updateProfile } = await import("@/lib/api");
                const ok = await updateProfile({ study_program: studyProgram, study_year: studyYear });
                if (ok) toast("Customization saved!");
                else toast("Failed to save. Try again.");
              }}
              className="px-6 py-2.5 rounded-xl text-sm font-medium"
              style={{ background: "var(--accent)", color: "#fff" }}
            >
              Save Changes
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
