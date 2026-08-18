export function HomeView({ onGenerate }: { onGenerate: () => void }) {
  return (
    <div
      aria-labelledby="home-heading"
      className="relative isolate flex min-h-[calc(100vh-4rem)] items-start justify-center overflow-hidden bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-900 px-6 py-20 text-center text-white sm:px-12"
    >
      <div
        aria-hidden="true"
        className="absolute -top-40 left-1/2 h-[32rem] w-[32rem] -translate-x-1/2 rounded-full bg-indigo-500/25 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="absolute -right-28 bottom-0 h-96 w-96 rounded-full bg-emerald-400/15 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="absolute -bottom-48 -left-24 h-96 w-96 rounded-full bg-lime-300/10 blur-3xl"
      />

      <div className="relative mx-auto max-w-3xl">
        <h1
          id="home-heading"
          className="text-5xl font-black tracking-[-0.04em] text-balance sm:text-7xl"
        >
          Fitness planning built for you
        </h1>
        <p className="mx-auto mt-7 max-w-2xl text-base leading-8 text-slate-300 sm:text-xl">
          Generate a workout and nutrition plan based on your fitness goal, experience, schedule,
          equipment, and dietary preferences.
        </p>
        <button
          type="button"
          className="mt-10 rounded-2xl bg-gradient-to-r from-lime-300 to-emerald-400 px-8 py-4 text-base font-bold text-slate-950 shadow-xl shadow-emerald-950/30 transition hover:-translate-y-0.5 hover:from-lime-200 hover:to-emerald-300"
          onClick={onGenerate}
        >
          Generate a plan
        </button>

        <div className="mt-10 flex flex-wrap justify-center gap-3 text-sm text-slate-400">
          <span>Workout plans</span>
          <span>Nutrition plans</span>
          <span>Saved plan history</span>
        </div>
      </div>
    </div>
  );
}
