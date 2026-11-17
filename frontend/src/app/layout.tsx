import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "ROMEX",
  description: "Sistema interno de ROMEX Logística",
};

// Runs before the first paint so the saved theme is applied without a flash
const themeInitScript = `
try {
  var theme = localStorage.getItem("romex-theme");
  if (theme === "light" || theme === "dark") {
    document.documentElement.dataset.theme = theme;
  }
} catch (e) {}
`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
