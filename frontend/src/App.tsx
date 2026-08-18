import { AccountSettingsView } from "./account/AccountSettingsView";
import { AuthForm } from "./auth/AuthForm";
import { useAuth } from "./auth/useAuth";
import { HomeView } from "./home/HomeView";
import { AppNavigation } from "./navigation/AppNavigation";
import { useAppRoute } from "./navigation/useAppRoute";
import { PlanGenerationView } from "./plan-generation/PlanGenerationView";
import { PlanDetailView } from "./plans/PlanDetailView";
import { PlanHistoryView } from "./plans/PlanHistoryView";

export function App() {
  const { error, logout, status, user } = useAuth();
  const { navigate, route } = useAppRoute();

  if (status === "loading" && route.name !== "home") {
    return (
      <main className="min-h-screen bg-slate-50 px-4 py-10 text-slate-900">
        <div className="mx-auto max-w-5xl">
          <h1 className="text-3xl font-bold tracking-tight">MyFitnessPlan</h1>
          <p className="mt-2 text-slate-600">Checking your session…</p>
        </div>
      </main>
    );
  }

  const authenticated = status === "authenticated" && user !== null;
  const publicHome = route.name === "home" || (authenticated && route.name === "auth");
  const authMode = route.name === "auth" ? route.mode : "login";

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-100/80 via-slate-100 to-emerald-100/70 bg-fixed text-slate-900">
      <AppNavigation authenticated={authenticated} currentRoute={route} navigate={navigate} />
      {authenticated ? (
        <main className={publicHome ? "min-w-0" : "min-w-0 px-4 py-6 sm:px-6 md:py-10 lg:px-8"}>
          <div className={publicHome ? "max-w-none" : "mx-auto max-w-6xl"}>
            {publicHome ? (
              <HomeView onGenerate={() => navigate({ name: "generate" })} />
            ) : route.name === "generate" ? (
              <PlanGenerationView
                onViewPlan={(planId) => navigate({ name: "plan-detail", planId })}
              />
            ) : route.name === "plans" ? (
              <PlanHistoryView
                onGenerate={() => navigate({ name: "generate" })}
                onViewPlan={(planId) => navigate({ name: "plan-detail", planId })}
              />
            ) : route.name === "plan-detail" ? (
              <PlanDetailView
                key={route.planId}
                planId={route.planId}
                onBack={() => navigate({ name: "plans" })}
              />
            ) : route.name === "account" ? (
              <AccountSettingsView email={user.email} error={error} logout={logout} />
            ) : (
              <section aria-labelledby="not-found-heading">
                <h2 id="not-found-heading">Page not found</h2>
                <p className="mt-2 text-slate-600">
                  The requested page is not part of MyFitnessPlan.
                </p>
                <button
                  type="button"
                  className="mt-4"
                  onClick={() => navigate({ name: "generate" })}
                >
                  Go to plan generation
                </button>
              </section>
            )}
          </div>
        </main>
      ) : route.name === "home" ? (
        <main className="min-w-0">
          <HomeView onGenerate={() => navigate({ name: "generate" })} />
        </main>
      ) : (
        <main className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-4 py-10 sm:px-6">
          <AuthForm key={authMode} initialMode={authMode} />
        </main>
      )}
    </div>
  );
}
