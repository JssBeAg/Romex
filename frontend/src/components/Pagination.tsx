"use client";

import type { Pagination as PaginationData } from "@/lib/listing";

type Props = {
  pagination: PaginationData;
  onPage: (page: number) => void;
  onPageSize?: (size: number) => void;
};

const SIZES = [10, 20, 50, 100];

// The pages to show: first, last and the ones around the current, with "…" in the gaps
function pageList(current: number, pages: number): (number | "gap")[] {
  const wanted = new Set([1, pages, current - 1, current, current + 1]);
  const sorted = [...wanted].filter((n) => n >= 1 && n <= pages).sort((a, b) => a - b);
  const result: (number | "gap")[] = [];
  sorted.forEach((n, index) => {
    if (index > 0 && n - sorted[index - 1] > 1) result.push("gap");
    result.push(n);
  });
  return result;
}

// "1-20 de 134" with the buttons to move between pages and the size of the page
export default function Pagination({ pagination, onPage, onPageSize }: Props) {
  const { page, pages, page_size: size, total } = pagination;
  const from = total === 0 ? 0 : (page - 1) * size + 1;
  const to = Math.min(page * size, total);

  return (
    <nav className="pagination" aria-label="Paginación">
      <span className="pagination-info">
        {total === 0 ? "Sin registros" : `${from}-${to} de ${total}`}
      </span>
      {pages > 1 && (
        <span className="pagination-pages">
          <button type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>
            Anterior
          </button>
          {pageList(page, pages).map((item, index) =>
            item === "gap" ? (
              <span key={`gap-${index}`} className="pagination-gap" aria-hidden="true">…</span>
            ) : (
              <button
                key={item}
                type="button"
                className={item === page ? "page-current" : undefined}
                aria-current={item === page ? "page" : undefined}
                onClick={() => onPage(item)}
              >
                {item}
              </button>
            )
          )}
          <button type="button" disabled={page >= pages} onClick={() => onPage(page + 1)}>
            Siguiente
          </button>
        </span>
      )}
      {onPageSize && (
        <label className="pagination-size">
          Filas por página{" "}
          <select value={size} onChange={(e) => onPageSize(Number(e.target.value))}>
            {SIZES.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      )}
    </nav>
  );
}
