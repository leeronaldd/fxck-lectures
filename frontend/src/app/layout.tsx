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
  title: "Fxck Lectures — Replace Bad Professors with a 20-Min Read",
  description:
    "Turns that one bad professor's 2-hour lecture into a 20-minute read that actually makes sense. Textbook-verified, exam-aware, and free to try.",
  metadataBase: new URL("https://klareai.com"),
  openGraph: {
    title: "Fxck Lectures — Replace Bad Professors with a 20-Min Read",
    description:
      "Turns that one bad professor's 2-hour lecture into a 20-minute read that actually makes sense. Textbook-verified, exam-aware, and free to try.",
    url: "https://klareai.com",
    siteName: "Klare",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Fxck Lectures — Replace Bad Professors with a 20-Min Read",
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
      </body>
    </html>
  );
}
