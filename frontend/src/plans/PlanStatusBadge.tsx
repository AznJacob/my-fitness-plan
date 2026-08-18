import type { PlanStatus } from "./api";

const STATUS_STYLES: Record<PlanStatus, string> = {
  active: "bg-emerald-100 text-emerald-800",
  inactive: "bg-slate-100 text-slate-700",
  archived: "bg-amber-100 text-amber-800",
};

export function PlanStatusBadge({ status }: { status: PlanStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${STATUS_STYLES[status]}`}
    >
      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      {status[0].toUpperCase() + status.slice(1)}
    </span>
  );
}
