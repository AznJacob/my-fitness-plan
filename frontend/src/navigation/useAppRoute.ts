import { useCallback, useEffect, useState } from "react";

export type AppRoute =
  | { name: "home" }
  | { name: "generate" }
  | { name: "plans" }
  | { name: "plan-detail"; planId: string }
  | { name: "account" }
  | { name: "auth"; mode: "login" | "register" }
  | { name: "not-found" };

export type NavigableRoute = Exclude<AppRoute, { name: "not-found" }>;

const ROUTE_PATHS = {
  home: "/",
  generate: "/plans/new",
  plans: "/plans",
  account: "/account",
  auth: "/auth",
} as const;

function routeFromLocation(pathname: string, search: string): AppRoute {
  if (pathname === ROUTE_PATHS.home) {
    return { name: "home" };
  }
  if (pathname === ROUTE_PATHS.generate) {
    return { name: "generate" };
  }
  if (pathname === ROUTE_PATHS.plans) {
    return { name: "plans" };
  }
  if (pathname === ROUTE_PATHS.account) {
    return { name: "account" };
  }
  if (pathname === ROUTE_PATHS.auth) {
    return {
      name: "auth",
      mode: new URLSearchParams(search).get("mode") === "register" ? "register" : "login",
    };
  }
  const planDetailMatch = /^\/plans\/([0-9a-fA-F-]{36})$/.exec(pathname);
  if (planDetailMatch?.[1] !== undefined) {
    return { name: "plan-detail", planId: planDetailMatch[1] };
  }
  return { name: "not-found" };
}

export function pathForRoute(route: NavigableRoute): string {
  if (route.name === "plan-detail") {
    return `/plans/${route.planId}`;
  }
  if (route.name === "auth") {
    return route.mode === "register" ? "/auth?mode=register" : "/auth";
  }
  return ROUTE_PATHS[route.name];
}

export function useAppRoute() {
  const [route, setRoute] = useState<AppRoute>(() =>
    routeFromLocation(window.location.pathname, window.location.search),
  );

  useEffect(() => {
    const handlePopState = () =>
      setRoute(routeFromLocation(window.location.pathname, window.location.search));
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
