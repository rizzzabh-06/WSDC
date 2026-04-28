import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "WSDC — Web3 Secure Development Co-Pilot",
  description:
    "AI-powered security review for Web3 & backend systems. Catch vulnerabilities before they ship with context-aware, developer-first security analysis.",
  keywords: [
    "Web3 security",
    "smart contract audit",
    "AI code review",
    "SAST",
    "shift-left security",
    "DeFi security",
    "GitHub PR review",
  ],
  openGraph: {
    title: "WSDC — Web3 Secure Development Co-Pilot",
    description:
      "AI-powered security review for Web3 & backend systems. Catch vulnerabilities before they ship.",
    type: "website",
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
      className={`${inter.variable} ${jetbrainsMono.variable} h-full`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
