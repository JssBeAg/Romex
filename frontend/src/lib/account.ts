import type { User } from "./api";
import { request } from "./http";

export type PasswordInput = {
  current_password: string;
  new_password: string;
  confirm_password: string;
};

const PATH = "auth/cambiar-contrasena/";

// Asks the server to check the passwords without changing anything (?validar=1)
export const validatePasswordChange = (input: PasswordInput) =>
  request<{ errors: Record<string, string[]> }>(`${PATH}?validar=1`, "POST", input);

export const changePassword = (input: PasswordInput) =>
  request<{ user: User }>(PATH, "POST", input);
