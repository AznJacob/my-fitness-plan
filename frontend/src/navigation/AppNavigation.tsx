import type { MouseEvent } from "react";

import { pathForRoute, type AppRoute, type NavigableRoute } from "./useAppRoute";

interface AppNavigationProps {
  currentRoute: AppRoute;
  navigate: (route: NavigableRoute) => void;
}

const LINKS: { label: string; route: NavigableRoute }[] = [
  { label: "Generate plan", route: { name: "generate" } },
  { label: "Plan history", route: { name: "plans" } },
  { label: "Profile", route: { name: "profile" } },
  { label: "Account settings", route: { name: "account" } },
];

export function AppNavigation({ currentRoute, navigate }: AppNavigationProps) {
  function handleNavigation(event: MouseEvent<HTMLAnchorElement>, route: NavigableRoute) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    event.preventDefault();
    navigate(route);
  }

  return (
    <nav aria-label="Main navigation" className="mb-6 flex flex-wrap gap-2">
      {LINKS.map((link) => {
        const active =
          currentRoute.name === link.route.name ||
          (currentRoute.name === "plan-detail" && link.route.name === "plans");
        return (
          <a
            key={link.route.name}
            href={pathForRoute(link.route)}
            aria-current={active ? "page" : undefined}
            className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
              active
                ? "border-slate-900 bg-slate-900 text-white"
                : "border-slate-300 bg-white text-slate-700 hover:bg-slate-100"
            }`}
            onClick={(event) => handleNavigation(event, link.route)}
          >
            {link.label}
          </a>
        );
      })}
    </nav>
  );
}
