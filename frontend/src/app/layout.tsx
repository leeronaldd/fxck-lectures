import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import AppShell from "@/components/AppShell";
import AuthProvider from "@/components/AuthProvider";
import { Toaster } from "sonner";
import { Analytics } from "@vercel/analytics/react";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Klare — Lectures, taught better",
  description:
    "Turns that one bad professor's 2-hour lecture into a 20-minute read that actually makes sense. Textbook-verified, exam-aware, and free to try. Built for medical, biomed, and nursing students.",
  metadataBase: new URL("https://klareai.com"),
  keywords: [
    "AI study tool",
    "bad professor",
    "lecture notes AI",
    "medical student study tool",
    "biomed study app",
    "AI lecture replacement",
    "Klare",
    "klareai",
    "NotebookLM alternative",
    "university study AI",
  ],
  openGraph: {
    title: "Klare — Lectures, taught better",
    description:
      "Turns that one bad professor's 2-hour lecture into a 20-minute read that actually makes sense. Textbook-verified, exam-aware, and free to try.",
    url: "https://klareai.com",
    siteName: "Klare",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Klare — Lectures, taught better",
    description:
      "Turns that one bad professor's 2-hour lecture into a 20-minute read that actually makes sense. Free to try.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full flex flex-col">
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
        <Toaster
          theme="dark"
          position="bottom-right"
          toastOptions={{
            style: {
              background: "rgba(20, 20, 25, 0.95)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              color: "#F5F5F7",
              backdropFilter: "blur(20px)",
            },
          }}
        />
        <Analytics />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "SoftwareApplication",
              name: "Klare",
              applicationCategory: "EducationalApplication",
              operatingSystem: "Web",
              url: "https://klareai.com",
              description:
                "AI study tool that transforms bad university lecture recordings into clear, textbook-verified study documents. Re-teaches concepts from scratch using a tutor-style approach. Built for medical, biomed, nursing, and health science students.",
              offers: {
                "@type": "Offer",
                price: "0",
                priceCurrency: "AUD",
                description: "Free tier: 1 lecture, no credit card required",
              },
              audience: {
                "@type": "EducationalAudience",
                educationalRole: "student",
              },
              publisher: {
                "@type": "Organization",
                name: "Klare",
                url: "https://klareai.com",
                email: "hello@klareai.com",
              },
            }),
          }}
        />
      </body>
    </html>
  );
}
