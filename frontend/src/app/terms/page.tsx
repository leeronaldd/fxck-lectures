"use client";

import { useRouter } from "next/navigation";

export default function TermsPage() {
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
          Terms of Service
        </h1>
        <p className="text-sm mb-10" style={{ color: "var(--text-muted)" }}>
          Last updated: 16 April 2026
        </p>

        <div className="space-y-8 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          <Section title="1. Who we are">
            Klare (&ldquo;we&rdquo;, &ldquo;us&rdquo;) operates Klare, an AI-powered tool that
            transforms lecture recordings and transcripts into structured study documents.
            By creating an account or using the service at klareai.com, you agree to these terms.
            If you do not agree, do not use the service.
          </Section>

          <Section title="2. Eligibility and accounts">
            You must be at least 16 years old to use Klare. You are responsible for keeping
            your sign-in credentials secure and for all activity on your account. Notify us
            promptly at hello@klareai.com if you suspect unauthorised access.
          </Section>

          <Section title="3. Acceptable use">
            You agree not to: upload material you do not have the right to process; reverse
            engineer, scrape, or attempt to circumvent usage limits; use the service to
            generate content that is illegal, infringing, defamatory, or violates anyone&rsquo;s
            privacy; or resell or redistribute outputs as a substitute service. We may
            suspend or terminate accounts that violate these rules.
          </Section>

          <Section title="4. Your content">
            You retain ownership of the lecture audio, video, slides and transcripts you
            upload. You grant us a limited licence to process that content for the sole
            purpose of generating your study documents. We do not use your content to train
            our or any third party&rsquo;s AI models.
          </Section>

          <Section title="5. AI-generated outputs">
            Outputs are produced by large language models and may contain errors,
            omissions, or hallucinations. Klare is a study aid, not a substitute for
            verified textbooks, qualified instructors, or clinical judgment. Do not rely on
            outputs for medical, legal, or other professional decisions. You are responsible
            for verifying any factual claim before relying on it.
          </Section>

          <Section title="6. Subscriptions, billing and refunds">
            <p className="mb-3">
              Free accounts include a small lifetime allowance. Paid plans (Pro, Max) are
              billed monthly or yearly in advance, in Australian Dollars (AUD), through Stripe.
              Prices and limits are shown at klareai.com/settings.
            </p>
            <p className="mb-3">
              <strong>Cancellation:</strong> you can cancel at any time from the Billing tab
              in Settings. Cancellation takes effect at the end of your current billing
              period; you keep access until then. We do not auto-refund unused portions of a
              billing period.
            </p>
            <p>
              <strong>Refunds:</strong> if you are a new subscriber and the service does not
              work for you, email hello@klareai.com within 7 days of your first paid charge
              and we will refund it in full, no questions asked. Outside that window, refunds
              are issued at our discretion. Payment processor fees are non-refundable.
            </p>
          </Section>

          <Section title="7. Service availability">
            We work to keep Klare available but do not guarantee uninterrupted service.
            Scheduled maintenance, third-party outages (e.g. Google Cloud, Vertex AI,
            Supabase, Stripe), or sudden traffic spikes may cause downtime or processing
            delays. We are not liable for losses resulting from temporary unavailability.
          </Section>

          <Section title="8. Third-party services">
            Klare relies on Google Vertex AI, Groq, Supabase, Stripe, Vercel and Cloudflare
            to deliver the service. Your content is transmitted to and processed by these
            providers under their respective terms and privacy policies.
          </Section>

          <Section title="9. Limitation of liability">
            To the maximum extent permitted by law, our total liability for any claim
            arising from your use of Klare is capped at the amount you have paid us in the
            twelve months preceding the claim. We are not liable for indirect, consequential,
            or special damages, including loss of grades, missed deadlines, or academic
            outcomes. Nothing in these terms limits rights you have under the Australian
            Consumer Law that cannot be excluded.
          </Section>

          <Section title="10. Termination">
            You may delete your account at any time by emailing hello@klareai.com. We may
            terminate or suspend your account if you violate these terms. On termination,
            your access ends and we will delete or anonymise your stored content within 30
            days, except where retention is required by law.
          </Section>

          <Section title="11. Changes to these terms">
            We may update these terms occasionally. Material changes will be posted at
            klareai.com/terms with an updated &ldquo;Last updated&rdquo; date. Continued use after
            changes take effect constitutes acceptance.
          </Section>

          <Section title="12. Governing law">
            These terms are governed by the laws of Queensland, Australia. Any disputes
            will be resolved in the courts of Queensland.
          </Section>

          <Section title="13. Contact">
            Questions, refunds, or account issues: <a href="mailto:hello@klareai.com" style={{ color: "var(--accent)" }}>hello@klareai.com</a>.
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
