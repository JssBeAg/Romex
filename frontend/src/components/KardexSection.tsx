"use client";

import { FormEvent, type ReactNode, useState } from "react";
import ExportButton from "@/components/ExportButton";
import Pagination from "@/components/Pagination";
import SortHeader from "@/components/SortHeader";
import { type FilterOption, type SectionPage, listKardexSection, sectionPath } from "@/lib/kardex";
import { type ListParams, useList } from "@/lib/listing";

export type SectionColumn<T> = {
  header: string;
  sort?: string; // the column the API sorts by (none: not sortable)
  cell: (row: T) => ReactNode;
};

// A filter of its own (besides the search and the dates, which every section has)
export type SectionFilter = {
  name: string; // query parameter
  label: string;
  all: string; // text of the "no filter" option
  options: FilterOption[] | ((page: SectionPage | null) => FilterOption[]);
};

type Props<T> = {
  unitId: number;
  section: string; // path of the section in the API, e.g. "mantenimientos"
  rowsKey: string; // where its rows are in the answer
  title: string;
  searchLabel: string;
  filters?: SectionFilter[];
  columns: SectionColumn<T>[];
  rowKey: (row: T) => string | number;
  empty: string;
};

/**
 * One section of the kardex: the filters (applied with Buscar, as in the bitácora), the table with
 * its own columns, sortable, paged by the server, and the PDF with the filters on screen.
 */
export default function KardexSection<T>({
  unitId,
  section,
  rowsKey,
  title,
  searchLabel,
  filters = [],
  columns,
  rowKey,
  empty,
}: Props<T>) {
  const blank: Record<string, string> = { q: "", date_from: "", date_to: "" };
  for (const filter of filters) blank[filter.name] = "";
  const [draft, setDraft] = useState(blank);

  const list = useList<T, SectionPage>({
    fetch: (params) => listKardexSection(unitId, section, params),
    rows: (data) => (data[rowsKey] as T[]) ?? [],
  });
  const params = list.params;
  // What the list shows now, without the page: the PDF exports exactly this
  const applied: ListParams = { ...params };
  delete applied.page;
  delete applied.page_size;

  function set(name: string, value: string) {
    setDraft((previous) => ({ ...previous, [name]: value }));
  }

  function apply(e: FormEvent) {
    e.preventDefault();
    list.update({ ...draft });
  }

  function clear() {
    setDraft(blank);
    list.update({ ...blank });
  }

  const id = (name: string) => `${section}-${name}`;
  const rows = list.page.items;

  return (
    <>
      <form onSubmit={apply} className="audit-filters" aria-label={`Filtros de ${title.toLowerCase()}`}>
        <p>
          <label htmlFor={id("q")}>{searchLabel}</label>
          <br />
          <input id={id("q")} value={draft.q} onChange={(e) => set("q", e.target.value)} />
        </p>
        {filters.map((filter) => {
          const options = typeof filter.options === "function" ? filter.options(list.page.data) : filter.options;
          return (
            <p key={filter.name}>
              <label htmlFor={id(filter.name)}>{filter.label}</label>
              <br />
              <select id={id(filter.name)} value={draft[filter.name]} onChange={(e) => set(filter.name, e.target.value)}>
                <option value="">{filter.all}</option>
                {options.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </p>
          );
        })}
        <p>
          <label htmlFor={id("date_from")}>Desde</label>
          <br />
          <input
            id={id("date_from")}
            type="date"
            value={draft.date_from}
            max={draft.date_to || undefined}
            onChange={(e) => set("date_from", e.target.value)}
          />
        </p>
        <p>
          <label htmlFor={id("date_to")}>Hasta</label>
          <br />
          <input
            id={id("date_to")}
            type="date"
            value={draft.date_to}
            min={draft.date_from || undefined}
            onChange={(e) => set("date_to", e.target.value)}
          />
        </p>
        <p className="audit-buttons">
          <button type="submit">Buscar</button>{" "}
          <button type="button" onClick={clear}>
            Limpiar
          </button>
        </p>
      </form>

      <div className="list-actions">
        <ExportButton path={sectionPath(unitId, section)} params={applied} label={`Exportar ${title.toLowerCase()} a PDF`} />
      </div>

      {list.error && <p role="alert">{list.error}</p>}

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {columns.map((column) =>
                column.sort ? (
                  <SortHeader key={column.header} column={column.sort} order={params.order as string | undefined} onSort={list.sortBy}>
                    {column.header}
                  </SortHeader>
                ) : (
                  <th key={column.header}>{column.header}</th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {!list.loading && rows.length === 0 && (
              <tr>
                <td colSpan={columns.length}>{empty}</td>
              </tr>
            )}
            {rows.map((row) => (
              <tr key={rowKey(row)}>
                {columns.map((column) => (
                  <td key={column.header}>{column.cell(row)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination
        pagination={list.page.pagination}
        onPage={(page) => list.update({ page })}
        onPageSize={(size) => list.update({ page_size: size })}
      />
    </>
  );
}

/** A long text in a cell: the first characters and «ver más»; the whole text when it is opened. */
export function LongText({ text, limit = 80 }: { text: string | null | undefined; limit?: number }) {
  if (!text) return <>—</>;
  if (text.length <= limit) return <>{text}</>;
  return (
    <details className="long-text">
      <summary>
        <span className="preview">{text.slice(0, limit).trimEnd()}… </span>
        <span className="more">ver más</span>
        <span className="more less">ver menos</span>
      </summary>
      {text}
    </details>
  );
}
