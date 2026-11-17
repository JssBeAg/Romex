import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser, type User } from "@/lib/api";

// For pages only some roles can use: sends people without a session to the login and
// reports whether the logged-in user's role is one of the allowed ones.
export function useRoleGuard(allowedRoles: string[]) {
  const router = useRouter();
  const [state, setState] = useState<{
    loading: boolean;
    allowed: boolean;
    user: User | null;
  }>({ loading: true, allowed: false, user: null });

  // The list is compared by content so a new array on every render does not re-run this
  const key = allowedRoles.join("|");

  useEffect(() => {
    getCurrentUser().then((user) => {
      if (!user) {
        router.replace("/login");
        return;
      }
      setState({ loading: false, allowed: key.split("|").includes(user.role), user });
    });
  }, [router, key]);

  return state;
}
