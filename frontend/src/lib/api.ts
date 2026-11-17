export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type User = {
  id: number;
  enrollment_id: string;
  first_name: string;
  paternal_surname: string;
  maternal_surname: string;
  role: string;
  is_staff: boolean;
  must_change_password: boolean;
  photo_url: string | null; // API path of the profile photo; null when there is none
};

// Always ask for a fresh token: Django rotates it on login/logout
export async function getCsrfToken(): Promise<string> {
  const res = await fetch(`${API_URL}/api/auth/csrf/`, {
    credentials: "include",
  });
  const data = await res.json();
  return data.csrfToken;
}

export async function login(
  enrollmentId: string,
  password: string
): Promise<{ user?: User; error?: string }> {
  try {
    const csrfToken = await getCsrfToken();
    const res = await fetch(`${API_URL}/api/auth/login/`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({ enrollment_id: enrollmentId, password }),
    });
    if (res.status === 400) {
      return { error: "Ingresa tu matrícula y contraseña" };
    }
    if (res.status === 423) {
      // The account is locked after too many failed attempts: the server says for how long
      const body = await res.json().catch(() => ({}));
      return { error: body.error ?? "Cuenta bloqueada temporalmente. Intenta más tarde" };
    }
    if (res.status === 401) {
      return { error: "Matrícula o contraseña incorrectas" };
    }
    if (!res.ok) {
      return { error: "No se pudo iniciar sesión. Intenta de nuevo" };
    }
    const data = await res.json();
    return { user: data.user };
  } catch {
    return { error: "No se pudo conectar con el servidor" };
  }
}

export async function logout(): Promise<void> {
  const csrfToken = await getCsrfToken();
  await fetch(`${API_URL}/api/auth/logout/`, {
    method: "POST",
    credentials: "include",
    headers: { "X-CSRFToken": csrfToken },
  });
}

// Returns the logged-in user, or null if there is no active session
export async function getCurrentUser(): Promise<User | null> {
  try {
    const res = await fetch(`${API_URL}/api/auth/me/`, {
      credentials: "include",
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.user;
  } catch {
    return null;
  }
}
