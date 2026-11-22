import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth/AuthContext";
import { Layout, Logo } from "./components/Layout";
import { EmptyState, Spinner } from "./components/ui";
import { LoginPage, RegisterPage } from "./pages/AuthPages";
import { DashboardPage } from "./pages/DashboardPage";
import { MirrorsPage } from "./pages/MirrorsPage";
import { TrainPage } from "./pages/TrainPage";
import { WorkoutPage } from "./pages/WorkoutPage";
import { WorkoutsPage } from "./pages/WorkoutsPage";

function Offline({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="mx-auto max-w-md px-4 py-24">
      <div className="mb-6 flex justify-center">
        <Logo />
      </div>
      <EmptyState title="Can't reach the server">
        <p>Check that the backend is running, then try again.</p>
        <button type="button" className="btn-primary mt-4" onClick={onRetry}>
          Try again
        </button>
      </EmptyState>
    </div>
  );
}

export function App() {
  const { status, retry } = useAuth();

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    );
  }
  if (status === "offline") return <Offline onRetry={retry} />;

  if (status === "signedOut") {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        {/* Train is the first page you see after signing in */}
        <Route index element={<Navigate to="/train" replace />} />
        <Route path="train" element={<TrainPage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="workouts" element={<WorkoutsPage />} />
        <Route path="workouts/:id" element={<WorkoutPage />} />
        <Route path="mirrors" element={<MirrorsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
