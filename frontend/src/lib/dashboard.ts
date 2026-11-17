import { request } from "./http";

export type Dashboard = {
  months: number;
  period: { from: string; to: string };
  cards: {
    open_reports: number;
    unassigned_reports: number;
    reports_in_period: number;
    avg_resolution_days: number | null;
    maintenances_in_period: number;
    cost_in_period: string;
    avg_cost: string;
    active_units: number;
    inactive_units: number;
    low_stock_parts: number;
    preventive_overdue: number;
    preventive_upcoming: number;
    active_workers: number;
  };
  monthly: { labels: string[]; reports: number[]; preventive: number[]; corrective: number[]; cost: number[] };
  report_statuses: { label: string; count: number; closed: boolean }[];
  top_units_by_cost: { unit: string; total: string; count: number }[];
  top_units_by_reports: { unit: string; count: number }[];
  top_parts: { part: string; pieces: number }[];
  mechanic_workload: { mechanic: string; open_reports: number }[];
  low_stock: { id: number; name: string; stock: number; min_stock: number }[];
};

export const getDashboard = (months: number) =>
  request<Dashboard>(`dashboard/?months=${months}`, "GET");
