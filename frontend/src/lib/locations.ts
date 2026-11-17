import { useEffect, useState } from "react";

import { request } from "./http";

// States and municipalities of Mexico come from INEGI's web service (through the server)
export const getStates = () => request<{ options: string[] }>("ubicaciones/estados/", "GET");

export const getMunicipalities = (state: string) =>
  request<{ options: string[] }>(`ubicaciones/municipios/?estado=${encodeURIComponent(state)}`, "GET");

/** The states of INEGI, and the message to show when they could not be loaded. */
export function useStates(current = "") {
  const [states, setStates] = useState<string[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    getStates().then((res) => {
      if (!alive) return;
      if (!res.ok || !res.data) {
        setError(res.error ?? "No se pudo consultar el catálogo del INEGI.");
        return;
      }
      setError("");
      setStates(res.data.options);
    });
    return () => {
      alive = false;
    };
  }, []);

  return { states: withCurrent(states, current), error };
}

/** The saved value stays selectable even when INEGI's list no longer has it (or did not load). */
export function withCurrent(options: string[], current: string) {
  return current && !options.includes(current) ? [...options, current] : options;
}
