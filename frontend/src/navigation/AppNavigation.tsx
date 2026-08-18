import type { MouseEvent } from "react";

import { pathForRoute, type AppRoute, type NavigableRoute } from "./useAppRoute";

interface AppNavigationProps {
  authenticated: boolean;
  currentRoute: AppRoute;
  navigate: (route: NavigableRoute) => void;
}

const LINKS: { label: string; route: NavigableRoute }[] = [
  {
    label: "Home",
    route: { name: "home" },
  },
  {
    label: "Generate plan",
    route: { name: "generate" },
  },
  {
    label: "Plan history",
    route: { name: "plans" },
  },
];

export function AppNavigation({ authenticated, currentRoute, navigate }: AppNavigationProps) {
  const accountLink = authenticated
    ? ({ label: "Account settings", route: { name: "account" } } as const)
    : ({ label: "Sign Up", route: { name: "auth", mode: "register" } } as const);
  function handleNavigation(event: MouseEvent<HTMLAnchorElement>, route: NavigableRoute) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    event.preventDefault();
    navigate(route);
  }

  function isActive(route: NavigableRoute): boolean {
    return (
      currentRoute.name === route.name ||
      (currentRoute.name === "plan-detail" && route.name === "plans")
    );
  }

  function linkClass(active: boolean): string {
    return `rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${
      active
        ? "bg-white text-slate-950 shadow-sm"
        : "text-slate-300 hover:bg-white/10 hover:text-white"
    }`;
  }

  return (
    <header className="sticky top-0 z-20 border-b border-white/10 bg-gradient-to-r from-slate-950 via-slate-900 to-indigo-950 px-4 py-3 text-white shadow-lg shadow-slate-950/10 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-3">
        <a
          href={pathForRoute({ name: "home" })}
          className="text-lg font-black tracking-tight text-white"
          onClick={(event) => handleNavigation(event, { name: "home" })}
        >
          MyFitness Plan
        </a>

        <nav
          aria-label="Main navigation"
          className="order-3 flex w-full gap-1 sm:order-none sm:w-auto"
        >
          {LINKS.map((link) => {
            const active = isActive(link.route);
            return (
              <a
                key={link.route.name}
                href={pathForRoute(link.route)}
                aria-current={active ? "page" : undefined}
                className={linkClass(active)}
                onClick={(event) => handleNavigation(event, link.route)}
              >
                <span className="block truncate text-sm font-semibold">{link.label}</span>
              </a>
            );
          })}
        </nav>

        <a
          href={pathForRoute(accountLink.route)}
          aria-current={isActive(accountLink.route) ? "page" : undefined}
          className={`${
            authenticated
              ? linkClass(isActive(accountLink.route))
              : "rounded-lg bg-gradient-to-r from-lime-300 to-emerald-400 px-4 py-2 text-sm font-bold text-slate-950 transition hover:from-lime-200 hover:to-emerald-300"
          } ml-auto`}
          onClick={(event) => handleNavigation(event, accountLink.route)}
        >
          {accountLink.label}
        </a>
      </div>
    </header>
  );
}
