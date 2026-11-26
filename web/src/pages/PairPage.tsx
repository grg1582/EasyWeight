import { CheckCircle2, MonitorSmartphone, Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { useClaimPairing } from "../api/queries";
import { useAuth } from "../auth/AuthContext";
import { PageHeader } from "../components/ui";

/** 'k7qm3xpa' → 'K7QM-3XPA', as the mirror shows it */
export function prettyCode(code: string): string {
  const clean = code.replace(/[\s-]/g, "").toUpperCase();
  return clean.length === 8 ? `${clean.slice(0, 4)}-${clean.slice(4)}` : clean;
}

/** Opened by scanning a mirror's QR code (or typing its code on the Mirrors
 * page): connect that mirror to your account */
export function PairPage() {
  const code = (useParams().code ?? "").replace(/[\s-]/g, "").toUpperCase();
  const { user, signOut } = useAuth();
  const readOnly = user?.is_demo ?? false;
  const claim = useClaimPairing();
  const [name, setName] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    await claim.mutateAsync({ code, name }).catch(() => null);
  }

  const device = claim.data?.device;
  return (
    <>
      <PageHeader title="Connect a mirror" />
      <section className="card max-w-md p-6" aria-label="Connect a mirror">
        {device ? (
          <>
            <span className="icon-chip mb-4 h-11 w-11 rounded-xl bg-success/10 text-success">
              <CheckCircle2 aria-hidden className="h-5 w-5" />
            </span>
            <h2 className="text-lg font-semibold">“{device.name}” is connected</h2>
            <p className="mt-2 text-sm text-muted">
              The mirror picks it up within a few seconds. Its workouts will show up on your
              dashboard as you train.
            </p>
            <Link to="/dashboard" className="btn-primary mt-5">
              Go to the dashboard
            </Link>
          </>
        ) : readOnly ? (
          <>
            <span className="icon-chip mb-4 h-11 w-11 rounded-xl">
              <Sparkles aria-hidden className="h-5 w-5" />
            </span>
            <h2 className="text-lg font-semibold">The demo can't add mirrors</h2>
            <p className="mt-2 text-sm text-muted">
              Create an account to connect yours. It takes a few seconds.
            </p>
            <button type="button" className="btn-primary mt-5" onClick={() => void signOut()}>
              Create an account
            </button>
          </>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <span className="icon-chip h-11 w-11 rounded-xl">
              <MonitorSmartphone aria-hidden className="h-5 w-5" />
            </span>
            <p className="text-sm text-muted">
              Check that the mirror shows this code, then connect it to your account.
            </p>
            <div className="rounded-lg bg-ink/5 py-3 text-center font-mono text-2xl font-semibold tracking-widest">
              {prettyCode(code)}
            </div>
            <div>
              <label htmlFor="pair-name" className="label">
                Name (optional)
              </label>
              <input
                id="pair-name"
                className="input"
                placeholder="The name the mirror suggested"
                maxLength={100}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            {claim.isError && (
              <p role="alert" className="text-sm text-danger">
                {claim.error.message}
              </p>
            )}
            <button type="submit" className="btn-primary w-full" disabled={claim.isPending}>
              Connect mirror
            </button>
          </form>
        )}
      </section>
    </>
  );
}
