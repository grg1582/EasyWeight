import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

const links = [
  { to: "/", label: "Dashboard", end: true },
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
    <div className="min-h-screen">
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
  );
}
