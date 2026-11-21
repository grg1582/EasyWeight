import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { Logo } from "../components/Layout";

function AuthForm({ mode }: { mode: "login" | "register" }) {
  const { signIn, signUp } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const isLogin = mode === "login";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await (isLogin ? signIn : signUp)(email, password);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex justify-center text-lg">
          <Logo />
        </div>
        <form onSubmit={submit} className="card space-y-4 p-6" noValidate={false}>
          <div>
            <h1 className="text-xl font-semibold">{isLogin ? "Sign in" : "Create an account"}</h1>
            <p className="mt-1 text-sm text-muted">
              {isLogin
                ? "See your workouts from every mirror."
                : "Then connect your mirror, and every workout shows up here."}
            </p>
          </div>
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
          <button type="submit" className="btn-primary w-full" disabled={busy}>
            {busy ? "One moment…" : isLogin ? "Sign in" : "Create account"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-muted">
          {isLogin ? "No account yet? " : "Already have an account? "}
          <Link to={isLogin ? "/register" : "/login"} className="font-medium text-accent">
            {isLogin ? "Create one" : "Sign in"}
          </Link>
        </p>
      </div>
    </div>
  );
}

export function LoginPage() {
  return <AuthForm mode="login" />;
}

export function RegisterPage() {
  return <AuthForm mode="register" />;
}
