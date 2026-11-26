import { Camera, LayoutDashboard, ListChecks, LogOut, MonitorSmartphone, Sparkles } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { LiveProvider } from "../live/LiveContext";
import { LiveBadge } from "../live/LiveViews";

const links = [
  { to: "/train", label: "Train", icon: Camera },
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/workouts", label: "Workouts", icon: ListChecks },
  { to: "/mirrors", label: "Mirrors", icon: MonitorSmartphone },
];

export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`flex items-center gap-2 font-semibold tracking-tight ${className}`}>
      <img src="/favicon.svg" alt="" className="h-7 w-7" />
      EasyWeight
    </span>
  );
}

export function Layout() {
  const { user, signOut } = useAuth();
  const { pathname } = useLocation();
  return (
    <LiveProvider>
      <div className="min-h-screen">
        {user?.is_demo && (
          <div className="border-b border-accent/20 bg-accent/[0.07] px-4 py-2 text-center text-sm text-ink">
            <Sparkles aria-hidden className="mr-1.5 inline h-4 w-4 -translate-y-px text-accent" />
            You're looking at a demo with made-up workouts.{" "}
            <button type="button" className="link underline" onClick={() => void signOut()}>
              Create your own account
            </button>
          </div>
        )}
        <header className="sticky top-0 z-40 border-b border-line bg-surface/85 backdrop-blur-md supports-[backdrop-filter]:bg-surface/70">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-2 px-4 py-3">
            <Logo />
            <nav
              aria-label="Main"
              className="order-last -mx-1 flex w-full gap-1 overflow-x-auto sm:order-none sm:mx-0 sm:w-auto"
            >
              {links.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `flex shrink-0 items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                      isActive ? "bg-accent/10 text-accent" : "text-muted hover:bg-ink/5 hover:text-ink"
                    }`
                  }
                >
                  <Icon aria-hidden className="hidden h-4 w-4 sm:block" />
                  {label}
                </NavLink>
              ))}
            </nav>
            <div className="ml-auto flex items-center gap-3 text-sm">
              <LiveBadge />
              <span className="hidden max-w-[14rem] truncate text-muted md:inline">{user?.email}</span>
              <button type="button" className="btn-ghost px-3 py-1.5" onClick={() => void signOut()}>
                <LogOut aria-hidden className="h-4 w-4" />
                Sign out
              </button>
            </div>
          </div>
        </header>
        <main id="main" className="mx-auto max-w-6xl px-4 py-8 sm:py-10">
          {/* A short fade between pages */}
          <div key={pathname} className="motion-safe:animate-fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </LiveProvider>
  );
}
