import type { ReactNode } from "react";

import "./globals.css";
import { Nav } from "@/components/nav";
import { Providers } from "./providers";

export const metadata = {
  title: "Personalized Podcast Generator",
  description: "A fresh, personalized daily audio podcast from current news.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <Providers>
          <div className="mx-auto flex min-h-screen max-w-5xl flex-col px-4 pb-16">
            <Nav />
            <main className="flex-1">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
