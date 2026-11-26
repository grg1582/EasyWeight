import { ArrowRight, Camera, LineChart, Play, ShieldCheck } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { Logo } from "../components/Layout";
import { usePageTitle } from "../components/ui";

const FEATURES = [
  {
    icon: Camera,
    title: "Counts every rep from the camera",
    text: "Curls, lateral raises, overhead presses, squats and push-ups. The first rep tells which one.",
  },
  {
    icon: ShieldCheck,
    title: "Your video stays on your device",
    text: "The pose model runs in the browser or on the mirror. Only the reps are sent.",
  },
  {
    icon: LineChart,
    title: "Every set, live on your dashboard",
    text: "From any mirror or browser, as it happens, even after the network drops.",
  },
];

/** What the mirror shows mid-set, drawn like its display (hud.py) */
function MirrorPreview() {
  return (
    <div
      aria-hidden
      className="relative mx-auto aspect-[16/10] w-full max-w-md overflow-hidden rounded-2xl border border-white/10 bg-black shadow-2xl shadow-black/40"
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_120%,rgb(255_255_255/0.08),transparent_60%)]" />
      <div className="absolute left-[5%] top-[7%] text-white">
        <div className="text-lg tabular-nums leading-none sm:text-xl">17:52</div>
        <div className="mt-1 text-[10px] text-[#c8c8c8] sm:text-xs">22/11/2026</div>
      </div>
      <div className="absolute right-[5%] top-[7%] text-xs font-semibold text-[#3cd2ff] sm:text-sm">
        EasyWeight
      </div>
      <div className="absolute inset-x-0 top-[9%] text-center text-xs text-[#c8c8c8] sm:text-sm">
        Bicep curl
      </div>
      <div className="absolute inset-x-0 top-[22%] text-center text-[5.5rem] font-semibold leading-none tabular-nums text-[#78ff5a] sm:text-[7rem]">
        7
      </div>
      <div className="absolute inset-x-0 top-[72%] text-center text-xs tracking-[0.12em] text-[#c8c8c8] sm:text-sm">
        SET 2
      </div>
      {/* The arms, as the Train page shows them */}
      <div className="absolute inset-x-[12%] bottom-[8%] space-y-1.5">
        {[0.85, 0.7].map((value, k) => (
          <div key={k} className="h-1.5 rounded-full bg-white/10">
            <div className="h-full rounded-full bg-[#3cd2ff]" style={{ width: `${value * 100}%` }} />
          </div>
        ))}
      </div>
    </div>
  );
}

/** The left half on wide screens: what EasyWeight is, before you sign in */
function Hero() {
  return (
    <section className="relative hidden overflow-hidden bg-[#0b1220] text-white lg:flex lg:flex-col lg:gap-12 lg:p-12 xl:p-16">
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-[#2563c4]/30 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-40 right-0 h-96 w-96 rounded-full bg-[#3cd2ff]/10 blur-3xl" />
      <Logo className="relative text-lg" />
      <div className="relative my-auto max-w-lg">
        <p className="text-4xl font-semibold leading-tight tracking-tight xl:text-5xl">
          A mirror that counts your reps.
        </p>
        <p className="mt-4 text-lg text-white/70">
          EasyWeight watches your form with a camera, counts reps and sets, and keeps your training
          history. On a smart mirror, or right here in the browser.
        </p>
        <ul className="mt-8 space-y-5">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <li key={title} className="flex gap-4">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/10 text-[#7cc4ff]">
                <Icon aria-hidden className="h-[18px] w-[18px]" />
              </span>
              <span>
                <span className="block font-medium">{title}</span>
                <span className="block text-sm text-white/60">{text}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>
      {/* Only where there's room for it under the text */}
      <div className="relative hidden [@media(min-height:880px)]:block">
        <MirrorPreview />
      </div>
    </section>
  );
}

function AuthForm({ mode }: { mode: "login" | "register" }) {
  const { signIn, signUp, tryDemo } = useAuth();
  const { state } = useLocation(); // where to go after signing in, if somewhere
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const isLogin = mode === "login";
  usePageTitle(isLogin ? "Sign in" : "Create an account");

  async function run(action: () => Promise<void>) {
    setError(null);
    setBusy(true);
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setBusy(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void run(() => (isLogin ? signIn : signUp)(email, password));
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
      <Hero />
      <main className="flex items-center justify-center px-4 py-10 sm:py-16">
        <div className="w-full max-w-sm motion-safe:animate-fade-in">
          {/* On phones the hero is hidden: the logo and one line say what this is */}
          <div className="mb-8 text-center lg:hidden">
            <Logo className="justify-center text-lg" />
            <p className="mx-auto mt-3 max-w-xs text-sm text-muted">
              Counts your reps from the camera, on a smart mirror or in the browser.
            </p>
          </div>

          <div className="card p-5">
            <h2 className="font-semibold">See it in action</h2>
            <p className="mt-1 text-sm text-muted">
              Two months of made-up workouts, no account needed.
            </p>
            <button
              type="button"
              className="btn-primary btn-lg mt-4 w-full"
              disabled={busy}
              onClick={() => void run(tryDemo)}
            >
              <Play aria-hidden className="h-4 w-4 fill-current" />
              Try the demo
            </button>
          </div>

          <div className="my-6 flex items-center gap-3 text-xs text-faint">
            <span className="h-px flex-1 bg-line" />
            or use your account
            <span className="h-px flex-1 bg-line" />
          </div>

          <form onSubmit={submit} className="space-y-4">
            <h1 className="text-xl font-semibold tracking-tight">
              {isLogin ? "Sign in" : "Create an account"}
            </h1>
            {!isLogin && (
              <p className="-mt-2 text-sm text-muted">
                Then connect your mirror, and every workout shows up here.
              </p>
            )}
            <div>
              <label htmlFor="email" className="label">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                className="input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="password" className="label">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete={isLogin ? "current-password" : "new-password"}
                required
                minLength={isLogin ? undefined : 8}
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              {!isLogin && <p className="mt-1 text-xs text-faint">At least 8 characters.</p>}
            </div>
            {error && (
              <p role="alert" className="text-sm text-danger">
                {error}
              </p>
            )}
            <button type="submit" className="btn-ghost w-full" disabled={busy}>
              {busy ? "One moment…" : isLogin ? "Sign in" : "Create account"}
              {!busy && <ArrowRight aria-hidden className="h-4 w-4" />}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-muted">
            {isLogin ? "No account yet? " : "Already have an account? "}
            <Link to={isLogin ? "/register" : "/login"} state={state} className="link">
              {isLogin ? "Create one" : "Sign in"}
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}

export function LoginPage() {
  return <AuthForm mode="login" />;
}

export function RegisterPage() {
  return <AuthForm mode="register" />;
}
