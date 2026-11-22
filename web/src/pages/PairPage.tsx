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
  const readOnly = useAuth().user?.is_demo ?? false;
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
          <p className="text-sm text-muted">
            This is the demo, which can't add mirrors. Create an account to connect yours.
          </p>
        ) : (
          <form onSubmit={submit} className="space-y-4">
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
