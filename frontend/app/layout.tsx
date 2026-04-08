import type { Metadata } from "next";
import localFont from "next/font/local";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { RatingsLoader } from "@/components/RatingsLoader";
import "./globals.css";

const instrumentSerif = localFont({
  src: [
    {
      path: "../public/fonts/InstrumentSerif-Regular.ttf",
      weight: "400",
      style: "normal",
    },
    {
      path: "../public/fonts/InstrumentSerif-Italic.ttf",
      weight: "400",
      style: "italic",
    },
  ],
  variable: "--font-instrument-serif",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Pathfinder by NovaWealth",
  description:
    "An AI course scheduling assistant that reads your Degree Works audit and generates conflict-free class schedules in seconds.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${GeistSans.variable} ${GeistMono.variable} ${instrumentSerif.variable}`}
    >
      <body
        className="min-h-[100dvh] bg-[#FAFAF7] text-[#1A1A1A] antialiased"
        style={{ fontFamily: "var(--font-geist-sans), system-ui, sans-serif" }}
      >
        <RatingsLoader />
        {children}
        <div className="grain-overlay" />
      </body>
    </html>
  );
}
