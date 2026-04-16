"use client";

import { useRouter } from "next/navigation";

export default function PrivacyPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen relative overflow-hidden">
      <div className="orb orb-orange" style={{ width: 240, height: 240, top: "5%", right: "-5%" }} />
      <div className="orb orb-purple" style={{ width: 200, height: 200, bottom: "10%", left: "-5%" }} />

      <header
        className="relative z-10 flex items-center justify-between px-4 sm:px-6 py-2.5 h-[56px]"
        style={{
          background: "rgba(10, 10, 15, 0.7)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <button onClick={() => router.push("/")} className="hover:opacity-80 transition-opacity">
          <img src="/brand/logo-full-dark.svg" alt="Klare" className="h-7" />
        </button>
        <button
          onClick={() => router.back()}
          className="text-sm px-3 py-1.5 rounded-lg"
          style={{ color: "var(--text-muted)" }}
        >
          Back
        </button>
      </header>

      <main className="relative z-10 max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-bold mb-2" style={{ color: "var(--text-primary)" }}>
          Privacy Policy
        </h1>
        <p className="text-sm mb-10" style={{ color: "var(--text-muted)" }}>
          Last updated: 16 April 2026
        </p>

        <div className="space-y-8 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          <Section title="The short version">
            We collect the minimum we need to run Klare: your email, your lecture content,
            and basic usage logs. We don&rsquo;t sell your data. We don&rsquo;t train AI models on
            your content. You can delete your account and data at any time. This policy
            follows the Australian Privacy Principles (APPs).
          </Section>

          <Section title="1. What we collect">
            <ul className="list-disc pl-5 space-y-2">
              <li>
                <strong>Account info:</strong> email address, optional display name,
                optional study program and year of study (used to personalise outputs).
              </li>
              <li>
                <strong>Lecture content:</strong> audio, video, slides, transcripts and any
                related files you upload.
              </li>
              <li>
                <strong>Generated content:</strong> the study documents we produce from
                your uploads.
              </li>
              <li>
                <strong>Billing info:</strong> handled by Stripe. We never see your full
                card number; we only see the customer ID, subscription ID, plan, and
                payment status that Stripe sends us.
              </li>
              <li>
                <strong>Usage logs:</strong> request timestamps, file sizes, processing
                durations, error messages. Used to monitor performance, debug issues, and
                enforce fair-use limits.
              </li>
            </ul>
          </Section>

          <Section title="2. How we use it">
            Only to run the service: authenticate you, process your uploads into study
            documents, deliver them back, charge your subscription, fix bugs, and improve
            reliability. We do not sell, rent, or share your personal information with
            advertisers, data brokers, or any party not listed below.
          </Section>

          <Section title="3. Who processes your data on our behalf">
            <ul className="list-disc pl-5 space-y-2">
              <li>
                <strong>Supabase</strong> (USA, EU) — authentication and database storage
                for your account and session metadata.
              </li>
              <li>
                <strong>Google Cloud / Vertex AI</strong> (Sydney region for compute,
                global for AI inference) — hosts our backend and runs the Gemini models
                that generate your study documents. Google states inputs/outputs are not
                used to train its models when accessed via Vertex AI.
              </li>
              <li>
                <strong>Groq</strong> (USA) — performs audio transcription via Whisper.
                Audio is processed transiently and is not retained by Groq for training.
              </li>
              <li>
                <strong>Cloudflare</strong> (global) — DNS, email forwarding for hello@klareai.com.
              </li>
              <li>
                <strong>Vercel</strong> (USA) — hosts the klareai.com website.
              </li>
              <li>
                <strong>Stripe</strong> (USA, AU) — processes payments. Subject to
                Stripe&rsquo;s privacy policy.
              </li>
            </ul>
          </Section>

          <Section title="4. Where your data lives">
            Your account, lecture content and generated documents are stored on Google
            Cloud Storage and Supabase Postgres in the asia-pacific region. Some
            sub-processors (Vertex AI, Groq, Stripe) may process data in other regions
            including the United States.
          </Section>

          <Section title="5. AI training">
            We do not use your uploaded content or generated outputs to train our own
            models. We do not provide your content to any third party for the purpose of
            training their models. Inference providers (Vertex AI, Groq) are configured to
            process data without retention for training under their enterprise terms.
          </Section>

          <Section title="6. How long we keep things">
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Account data:</strong> until you delete your account.</li>
              <li><strong>Lecture sessions:</strong> until you delete them or your account.</li>
              <li><strong>Stripe billing records:</strong> as required by tax law (typically 7 years).</li>
              <li><strong>Server logs:</strong> 30 days, then automatically purged.</li>
            </ul>
          </Section>

          <Section title="7. Your rights">
            Under the APPs and similar laws, you have the right to access, correct, or
            delete the personal information we hold about you. To exercise these rights,
            email <a href="mailto:hello@klareai.com" style={{ color: "var(--accent)" }}>hello@klareai.com</a>.
            We will respond within 30 days. You can also delete your account directly from
            the Settings page, which removes your stored content within 30 days (Stripe
            billing records excepted).
          </Section>

          <Section title="8. Cookies and tracking">
            We use only essential cookies needed to keep you signed in. We do not use
            advertising or cross-site tracking cookies. Aggregate, non-identifying
            performance metrics may be collected via Vercel Analytics (no cookies, no
            individual user tracking).
          </Section>

          <Section title="9. Security">
            We use industry-standard encryption in transit (TLS) and at rest. Sign-in
            sessions are managed by Supabase using JWT tokens with rotation. Passwords are
            never stored in plain text. We will notify affected users within 72 hours of
            confirming any data breach that creates a real risk of serious harm, in line
            with the Notifiable Data Breaches scheme.
          </Section>

          <Section title="10. Children">
            Klare is not directed at children under 16. We do not knowingly collect
            personal information from anyone under 16. If you believe a child has provided
            us information, contact us and we will remove it.
          </Section>

          <Section title="11. Changes to this policy">
            Material changes will be posted at klareai.com/privacy with an updated
            &ldquo;Last updated&rdquo; date. We will email you when changes meaningfully affect how
            we handle your data.
          </Section>

          <Section title="12. Contact">
            Privacy questions or requests: <a href="mailto:hello@klareai.com" style={{ color: "var(--accent)" }}>hello@klareai.com</a>.
          </Section>
        </div>
      </main>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-base font-semibold mb-3" style={{ color: "var(--text-primary)" }}>
        {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}
