import type { ReactNode } from "react";
import AppShell from "@/components/AppShell";

// Every screen after the login shares the header (logo, menu, theme and logout)
export default function AppLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
