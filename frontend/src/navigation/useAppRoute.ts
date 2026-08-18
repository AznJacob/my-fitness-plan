import { useCallback, useEffect, useState } from "react";

export type AppRoute =
  | { name: "generate" }
  | { name: "plans" }
  | { name: "plan-detail"; planId: string }
  | { name: "profile" }
  | { name: "account" }
  | { name: "not-found" };

export type NavigableRoute = Exclude<AppRoute, { name: "not-found" }>;

const ROUTE_PATHS = {
  generate: "/plans/new",
  plans: "/plans",
  profile: "/profile",
  account: "/account",
} as const;

function routeFromPathname(pathname: string): AppRoute {
  if (pathname === "/" || pathname === ROUTE_PATHS.generate) {
    return { name: "generate" };
  }
  if (pathname === ROUTE_PATHS.plans) {
    return { name: "plans" };
  }
  if (pathname === ROUTE_PATHS.profile) {
    return { name: "profile" };
  }
  if (pathname === ROUTE_PATHS.account) {
    return { name: "account" };
  }
  const planDetailMatch = /^\/plans\/([0-9a-fA-F-]{36})$/.exec(pathname);
  if (planDetailMatch?.[1] !== undefined) {
    return { name: "plan-detail", planId: planDetailMatch[1] };
  }
  return { name: "not-found" };
}

export function pathForRoute(route: NavigableRoute): string {
  return route.name === "plan-detail" ? `/plans/${route.planId}` : ROUTE_PATHS[route.name];
}

export function useAppRoute() {
  const [route, setRoute] = useState<AppRoute>(() => routeFromPathname(window.location.pathname));

  useEffect(() => {
    const handlePopState = () => setRoute(routeFromPathname(window.location.pathname));
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = useCallback((nextRoute: NavigableRoute) => {
    const nextPath = pathForRoute(nextRoute);
    if (window.location.pathname !== nextPath) {
      window.history.pushState({}, "", nextPath);
    }
    setRoute(nextRoute);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  return { navigate, route };
}
