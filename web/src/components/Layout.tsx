import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { LiveProvider } from "../live/LiveContext";
import { LiveBadge } from "../live/LiveViews";

const links = [
  { to: "/train", label: "Train", end: false },
  { to: "/dashboard", label: "Dashboard", end: false },
  { to: "/workouts", label: "Workouts", end: false },
  { to: "/mirrors", label: "Mirrors", end: false },
];

export function Logo() {
  return (
    <span className="flex items-center gap-2 font-semibold tracking-tight">
      <img src="/favicon.svg" alt="" className="h-6 w-6" />
      EasyWeight
    </span>
  );
}

export function Layout() {
  const { user, signOut } = useAuth();
  return (
    <LiveProvider>
      <div className="min-h-screen">
        {user?.is_demo && (
          <div className="bg-accent px-4 py-2 text-center text-sm text-accent-ink">
            You're looking at a demo with made-up workouts.{" "}
            <button
              type="button"
              className="font-semibold underline underline-offset-2"
              onClick={() => void signOut()}
            >
              Create your own account
            </button>
          </div>
        )}
        <header className="border-b border-line bg-surface">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
            <Logo />
            <nav className="order-last flex w-full gap-1 sm:order-none sm:w-auto">
              {links.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.end}
                  className={({ isActive }) =>
                    `rounded-lg px-3 py-1.5 text-sm font-medium ${
                      isActive ? "bg-accent/10 text-accent" : "text-muted hover:text-ink"
                    }`
                  }
                >
                  {link.label}
                </NavLink>
              ))}
            </nav>
            <div className="ml-auto flex items-center gap-3 text-sm">
              <LiveBadge />
              <span className="hidden text-muted md:inline">{user?.email}</span>
              <button type="button" className="btn-ghost px-3 py-1.5" onClick={() => void signOut()}>
                Sign out
              </button>
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8">
          <Outlet />
        </main>
      </div>
    </LiveProvider>
  );
}
