"use client";

import { Headphones } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/history", label: "History" },
  { href: "/settings", label: "Settings" },
  { href: "/analytics", label: "Analytics" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-10 -mx-4 mb-6 flex items-center justify-between gap-4 border-b border-border bg-background/70 px-4 py-3 backdrop-blur">
      <Link href="/" className="flex items-center gap-2 font-semibold">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-primary-foreground">
          <Headphones size={18} />
        </span>
        <span className="hidden sm:inline">Daily Cast</span>
      </Link>
      <nav className="flex items-center gap-1 text-sm">
        {links.map((l) => {
          const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
          return (
            <Link
              key={l.href}
              href={l.href}
              className={cn(
                "rounded-md px-3 py-1.5 transition-colors",
                active
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {l.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
