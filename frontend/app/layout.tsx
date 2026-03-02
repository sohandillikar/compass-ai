import type { Metadata } from "next";
import { Source_Sans_3 } from "next/font/google";
import "./globals.css";

const aggieSans = Source_Sans_3({
  variable: "--font-aggie-sans",
  subsets: ["latin"],
  weight: ["400", "600"],
});

export const metadata: Metadata = {
  title: "Compass AI",
  description: "Compass AI",
  icons: {
    icon: "/aggie.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${aggieSans.variable} antialiased min-h-dvh overflow-hidden`}>
        {children}
      </body>
    </html>
  );
}
