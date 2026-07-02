import type { Metadata } from "next";
import { Quicksand } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const quicksand = Quicksand({
  subsets: ["latin"],
  weight: ["600", "700"],
  variable: "--font-quicksand",
});

export const metadata: Metadata = {
  title: "Bargain Hunters",
  description: "Track the best deals from your favourite Kenyan retailers",
  icons: {
    icon: "/favicon.png",
    shortcut: "/favicon.png",
    apple: "/favicon.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={quicksand.variable}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
