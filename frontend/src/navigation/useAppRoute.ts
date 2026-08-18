import { useCallback, useEffect, useState } from "react";

export type AppRoute = "generate" | "profile" | "account" | "not-found";

const ROUTE_PATHS: Record<Exclude<AppRoute, "not-found">, string> = {
  generate: "/plans/new",
  profile: "/profile",
  account: "/account",
};

function routeFromPathname(pathname: string): AppRoute {
  if (pathname === "/" || pathname === ROUTE_PATHS.generate) {
    return "generate";
  }
  if (pathname === ROUTE_PATHS.profile) {
    return "profile";
  }
  if (pathname === ROUTE_PATHS.account) {
    return "account";
  }
  return "not-found";
}

export function pathForRoute(route: Exclude<AppRoute, "not-found">): string {
  return ROUTE_PATHS[route];
}

export function useAppRoute() {
  const [route, setRoute] = useState<AppRoute>(() => routeFromPathname(window.location.pathname));

  useEffect(() => {
    const handlePopState = () => setRoute(routeFromPathname(window.location.pathname));
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = useCallback((nextRoute: Exclude<AppRoute, "not-found">) => {
    const nextPath = pathForRoute(nextRoute);
    if (window.location.pathname !== nextPath) {
      window.history.pushState({}, "", nextPath);
    }
    setRoute(nextRoute);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  return { navigate, route };
}
