import { MANAGER_ROLE } from "@/lib/roles";
import { useRoleGuard } from "@/lib/useRoleGuard";

// For pages only the manager role can use
export function useManagerGuard() {
  return useRoleGuard([MANAGER_ROLE]);
}
