"use client";

import { type ReactNode, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import Avatar from "@/components/Avatar";
import { getCurrentUser, logout, type User } from "@/lib/api";
import { NOTIFICATIONS_CHANGED, getUnreadCount } from "@/lib/notifications";
import { MANAGER_ROLE, MECHANIC_ROLE, OPERATOR_ROLE } from "@/lib/roles";
import { useTheme } from "@/lib/theme";
import styles from "./AppShell.module.css";

type NavItem = { href: string; label: string };

// The menu depends on the role (the backend enforces the permissions; this only decides what to show)
export function navItemsFor(role: string): NavItem[] {
  const items: NavItem[] = [{ href: "/", label: "Inicio" }];
  if (role === MANAGER_ROLE) items.push({ href: "/dashboard", label: "Dashboard" });
  if (role === MANAGER_ROLE || role === MECHANIC_ROLE || role === OPERATOR_ROLE) {
    items.push({
      href: "/reportes",
      label: role === OPERATOR_ROLE ? "Mis reportes" : "Reportes de fallas",
    });
  }
  if (role === MANAGER_ROLE || role === OPERATOR_ROLE) {
    items.push({
      href: "/checklists",
      label: role === OPERATOR_ROLE ? "Mis checklists" : "Checklists",
    });
  }
  if (role === MANAGER_ROLE || role === MECHANIC_ROLE) {
    items.push({
      href: "/diagnosticos",
      label: role === MECHANIC_ROLE ? "Mis diagnósticos" : "Diagnósticos",
    });
    items.push({
      href: "/mantenimientos",
      label: role === MECHANIC_ROLE ? "Mis mantenimientos" : "Mantenimientos",
    });
    items.push({ href: "/preventivo", label: "Preventivo" });
  }
  if (role === MANAGER_ROLE) {
    items.push({ href: "/trabajadores", label: "Trabajadores" });
    items.push({ href: "/unidades", label: "Unidades" });
    items.push({ href: "/refacciones", label: "Refacciones" });
    items.push({ href: "/kardex", label: "Kardex" });
    items.push({ href: "/bitacora", label: "Bitácora" });
  }
  return items;
}

// Sun (shown in dark mode, click for light) and moon (shown in light mode)
function ThemeIcon({ dark }: { dark: boolean }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {dark ? (
        <>
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </>
      ) : (
        <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
      )}
    </svg>
  );
}

function BellIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.7 21a2 2 0 0 1-3.4 0" />
    </svg>
  );
}

export default function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    getCurrentUser().then(setUser);
  }, [pathname]);

  // Number of unread notifications: asked every minute, when the page changes and when the
  // notifications page marks some as read
  const [unread, setUnread] = useState(0);
  const signedIn = user !== null;
  useEffect(() => {
    if (!signedIn) return;
    let cancelled = false;
    const refresh = () =>
      getUnreadCount().then((res) => {
        if (!cancelled && res.ok && res.data) setUnread(res.data.unread);
      });
    refresh();
    const timer = setInterval(refresh, 60000);
    window.addEventListener(NOTIFICATIONS_CHANGED, refresh);
    return () => {
      cancelled = true;
      clearInterval(timer);
      window.removeEventListener(NOTIFICATIONS_CHANGED, refresh);
    };
  }, [signedIn, pathname]);

  // A user who must choose a new password cannot use anything else until they do
  const mustChange = user?.must_change_password ?? false;
  useEffect(() => {
    if (mustChange && pathname !== "/cambiar-contrasena") router.replace("/cambiar-contrasena");
  }, [mustChange, pathname, router]);

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  function isActive(href: string) {
    return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
  }

  const items = user && !mustChange ? navItemsFor(user.role) : [];

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div className={styles.bar}>
          <Link href="/" className={styles.brand} aria-label="ROMEX Logística, inicio">
            {/* Two logo versions: the theme tokens show the one that fits */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img className={styles.logoLight} src="/romex-logo.png" alt="ROMEX Logística" />
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img className={styles.logoDark} src="/romex-logo-dark.png" alt="" />
          </Link>

          <div className={styles.tools}>
            {user && (
              <span className={styles.user}>
                <Avatar
                  size="sm"
                  firstName={user.first_name}
                  paternalSurname={user.paternal_surname}
                  enrollmentId={user.enrollment_id}
                  photoUrl={user.photo_url}
                />
                <span className={styles.userName}>
                  {user.first_name} {user.paternal_surname}
                </span>
                <span className={styles.role}>{user.role}</span>
              </span>
            )}
            {theme && (
              <button
                type="button"
                className={styles.iconButton}
                onClick={toggleTheme}
                aria-label={theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
                title={theme === "dark" ? "Modo claro" : "Modo oscuro"}
              >
                <ThemeIcon dark={theme === "dark"} />
              </button>
            )}
            {user && !mustChange && (
              <Link href="/cambiar-contrasena" className={styles.accountLink} title="Cambiar mi contraseña">
                Contraseña
              </Link>
            )}
            {user && !mustChange && (
              <Link
                href="/notificaciones"
                className={`${styles.iconButton} ${styles.bell}`}
                aria-label={unread > 0 ? `Notificaciones: ${unread} sin leer` : "Notificaciones"}
                title="Notificaciones"
              >
                <BellIcon />
                {unread > 0 && <span className={styles.badge}>{unread > 99 ? "99+" : unread}</span>}
              </Link>
            )}
            {user && (
              <button type="button" className={styles.logout} onClick={handleLogout}>
                Cerrar sesión
              </button>
            )}
          </div>
        </div>

        {items.length > 0 && (
          <nav className={styles.nav} aria-label="Menú principal">
            {items.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={isActive(item.href) ? styles.navActive : styles.navLink}
                aria-current={isActive(item.href) ? "page" : undefined}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        )}
      </header>

      <div className="app-content">{children}</div>
    </div>
  );
}
