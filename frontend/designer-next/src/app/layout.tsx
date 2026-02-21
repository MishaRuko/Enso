import type { Metadata } from "next";
import { Space_Grotesk, Righteous } from "next/font/google";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "600"],
});

const righteous = Righteous({
  subsets: ["latin"],
  variable: "--font-display",
  weight: "400",
});

export const metadata: Metadata = {
  title: "AI Interior Designer",
  description: "Design your dream room with AI-powered furniture placement",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${spaceGrotesk.variable} ${righteous.variable}`}>
      <body>{children}</body>
    </html>
  );
}
