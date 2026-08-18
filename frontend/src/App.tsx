import { AccountLinking } from "./auth/AccountLinking";
import { AuthForm } from "./auth/AuthForm";
import { useAuth } from "./auth/useAuth";
import { AppNavigation } from "./navigation/AppNavigation";
import { useAppRoute } from "./navigation/useAppRoute";
import { PlanGenerationView } from "./plan-generation/PlanGenerationView";
import { ProfileForm } from "./profile/ProfileForm";

export function App() {
  const { error, logout, status, user } = useAuth();
  const { navigate, route } = useAppRoute();

  if (status === "loading") {
    return (
      <main className="min-h-screen bg-slate-50 px-4 py-10 text-slate-900">
        <div className="mx-auto max-w-5xl">
          <h1 className="text-3xl font-bold tracking-tight">MyFitnessPlan</h1>
          <p className="mt-2 text-slate-600">Checking your session…</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">MyFitnessPlan</h1>
          <p className="mt-2 text-slate-600">
            A personalized workout and nutrition planning application.
          </p>
        </header>
        {status === "authenticated" && user !== null ? (
          <div className="space-y-6">
            <section
              aria-labelledby="account-heading"
              className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 id="account-heading" className="text-xl font-semibold">
                    Your account
                  </h2>
                  <p className="mt-1 text-sm text-slate-600">Signed in as {user.email}</p>
                </div>
                <button
                  type="button"
                  className="w-fit rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-100 disabled:opacity-50"
                  onClick={() => void logout().catch(() => undefined)}
                >
                  Log out
                </button>
              </div>
              {error === null ? null : (
                <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">
                  {error}
                </p>
              )}
            </section>
            <AppNavigation currentRoute={route} navigate={navigate} />
            {route === "generate" ? (
              <PlanGenerationView onEditProfile={() => navigate("profile")} />
            ) : route === "profile" ? (
              <ProfileForm />
            ) : route === "account" ? (
              <AccountLinking />
            ) : (
              <section aria-labelledby="not-found-heading">
                <h2 id="not-found-heading">Page not found</h2>
                <p className="mt-2 text-slate-600">
                  The requested page is not part of MyFitnessPlan.
                </p>
                <button type="button" className="mt-4" onClick={() => navigate("generate")}>
                  Go to plan generation
                </button>
              </section>
            )}
          </div>
        ) : (
          <AuthForm />
        )}
      </div>
    </main>
  );
}
