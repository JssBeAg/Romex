"use client";

import type { ReactNode } from "react";

type Props = {
  column: string; // the name the API sorts by
  order: string | undefined; // current order: "column" or "-column"
  onSort: (column: string) => void;
  children: ReactNode;
};

// A table heading that sorts the list when it is clicked, with an arrow for the current order
export default function SortHeader({ column, order, onSort, children }: Props) {
  const active = order === column || order === `-${column}`;
  const descending = order === `-${column}`;
  return (
    <th aria-sort={active ? (descending ? "descending" : "ascending") : "none"}>
      <button type="button" className="sort-button" onClick={() => onSort(column)} title="Ordenar por esta columna">
        {children}
        <span className="sort-arrow" aria-hidden="true">
          {active ? (descending ? " ▼" : " ▲") : " ↕"}
        </span>
      </button>
    </th>
  );
}
