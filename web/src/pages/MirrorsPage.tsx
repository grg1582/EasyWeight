import { Globe, MonitorSmartphone, QrCode, Sparkles, Terminal, Trash2 } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import type { Device, DeviceCreated } from "../api/types";
import { useAddDevice, useDevices, useRemoveDevice } from "../api/queries";
import { useAuth } from "../auth/AuthContext";
import { EmptyState, ErrorNote, PageHeader, Spinner } from "../components/ui";
import { formatAgo, formatDate } from "../lib/format";

/** Sent something in the last 10 minutes: it's on */
function Status({ device }: { device: Device }) {
  const active =
    device.last_seen_at !== null && Date.now() - new Date(device.last_seen_at).getTime() < 600_000;
  return active ? (
    <span className="pill bg-success/10 text-success">
      <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-success" />
      Active
    </span>
  ) : (
    <span className="pill bg-ink/5 text-muted">Idle</span>
  );
}

function CopyBlock({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="rounded-lg bg-ink/5">
      <div className="flex items-center justify-between px-3 pt-2 text-xs text-faint">
        {label}
        <button
          type="button"
          className="rounded px-1.5 py-0.5 font-medium text-accent hover:bg-accent/10"
          onClick={() => {
            void navigator.clipboard?.writeText(text).then(() => setCopied(true));
          }}
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="whitespace-pre-wrap break-all p-3 pt-1.5 text-xs text-ink" aria-label={label}>
        {text}
      </pre>
    </div>
  );
}

function NewMirror({ device, onDone }: { device: DeviceCreated; onDone: () => void }) {
  const config = JSON.stringify(
    {
      api_url: window.location.origin,
      device_id: device.id,
      name: device.name,
      token: device.token,
    },
    null,
    2,
  );
  return (
    <div className="card border-accent/40 p-5" role="region" aria-label="New mirror">
      <h2 className="font-semibold">“{device.name}” is added</h2>
      <p className="mt-1 text-sm text-muted">
        Save this as <code className="rounded bg-ink/5 px-1">device/data/device.json</code> on the
        mirror. The token is shown only now: if you lose it, remove the mirror and add it again.
      </p>
      <div className="mt-4">
        <CopyBlock text={config} label="Mirror settings" />
      </div>
      <button type="button" className="btn-ghost mt-4" onClick={onDone}>
        Done
      </button>
    </div>
  );
}

/** The easy way: the mirror shows a QR code. Scanning it opens /pair/<code>;
 * a laptop without a camera can type the code here instead */
function PairWithCode() {
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const clean = code.replace(/[\s-]/g, "");
  return (
    <form
      className="card space-y-3 p-5"
      onSubmit={(event) => {
        event.preventDefault();
        navigate(`/pair/${clean.toUpperCase()}`);
      }}
    >
      <h2 className="flex items-center gap-2 font-semibold">
        <QrCode aria-hidden className="h-4 w-4 text-accent" />
        Connect with a QR code
      </h2>
      <p className="text-sm text-muted">
        On the mirror, run <code className="rounded bg-ink/5 px-1">python -m easyweight.pair</code>{" "}
        and scan the code it shows with your phone. Or type the code here:
      </p>
      <div className="flex gap-2">
        <label htmlFor="pair-code" className="sr-only">
          Code
        </label>
        <input
          id="pair-code"
          className="input font-mono uppercase tracking-widest"
          placeholder="K7QM-3XPA"
          maxLength={9}
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />
        <button type="submit" className="btn-primary" disabled={clean.length !== 8}>
          Next
        </button>
      </div>
    </form>
  );
}

export function MirrorsPage() {
  const readOnly = useAuth().user?.is_demo ?? false;
  const devices = useDevices();
  const add = useAddDevice();
  const remove = useRemoveDevice();
  const [name, setName] = useState("");
  const [created, setCreated] = useState<DeviceCreated | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const device = await add.mutateAsync(name.trim()).catch(() => null);
    if (device) {
      setCreated(device);
      setName("");
    }
  }

  return (
    <>
      <PageHeader title="Mirrors" subtitle="The mirrors that send workouts to your account" />

      <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
        <div className="space-y-4">
          {created && <NewMirror device={created} onDone={() => setCreated(null)} />}
          {devices.isPending ? (
            <Spinner />
          ) : devices.isError ? (
            <ErrorNote error={devices.error} onRetry={() => void devices.refetch()} />
          ) : devices.data.length === 0 ? (
            <EmptyState title="No mirrors yet" icon={MonitorSmartphone}>
              Add your first mirror with the form, or scan its QR code.
            </EmptyState>
          ) : (
            <ul className="card divide-y divide-line">
              {devices.data.map((d) => (
                <li
                  key={d.id}
                  className="flex flex-wrap items-center justify-between gap-3 px-5 py-4"
                >
                  <div className="flex min-w-0 items-center gap-4">
                  <span className="icon-chip">
                    {d.kind === "browser" ? (
                      <Globe aria-hidden className="h-[18px] w-[18px]" />
                    ) : (
                      <MonitorSmartphone aria-hidden className="h-[18px] w-[18px]" />
                    )}
                  </span>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2 font-medium">
                      {d.name}
                      <Status device={d} />
                    </div>
                    <div className="text-sm text-muted">
                      {d.kind === "browser" && "Workouts from the Train page · "}
                      {d.last_seen_at
                        ? `Last sent ${formatAgo(d.last_seen_at)}`
                        : "Hasn't sent anything yet"}
                      <span className="text-faint"> · added {formatDate(d.created_at)}</span>
                    </div>
                  </div>
                  </div>
                  {!readOnly && (
                    <button
                      type="button"
                      className="btn-danger px-3 py-1.5"
                      disabled={remove.isPending}
                      onClick={() => {
                        if (
                          window.confirm(
                            `Remove "${d.name}"? Its workouts are deleted too, and it can't send any more.`,
                          )
                        ) {
                          remove.mutate(d.id);
                        }
                      }}
                    >
                      <Trash2 aria-hidden className="h-4 w-4" />
                      Remove
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        {readOnly ? (
          <aside className="card h-fit border-accent/25 bg-accent/[0.04] p-5 text-sm text-muted">
            <h2 className="mb-2 flex items-center gap-2 font-semibold text-ink">
              <Sparkles aria-hidden className="h-4 w-4 text-accent" />
              This is the demo
            </h2>
            Its mirror sends made-up workouts. Create an account to connect your own mirror.
          </aside>
        ) : (
          <aside className="space-y-4">
            <form onSubmit={submit} className="card space-y-3 p-5">
              <h2 className="font-semibold">Add a mirror</h2>
              <div>
                <label htmlFor="mirror-name" className="label">
                  Name
                </label>
                <input
                  id="mirror-name"
                  className="input"
                  placeholder="Home mirror"
                  required
                  maxLength={100}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              {add.isError && (
                <p role="alert" className="text-sm text-danger">
                  {add.error.message}
                </p>
              )}
              <button
                type="submit"
                className="btn-primary w-full"
                disabled={add.isPending || !name.trim()}
              >
                Add mirror
              </button>
            </form>
            <PairWithCode />
            <div className="card p-5 text-sm text-muted">
              <h2 className="mb-2 flex items-center gap-2 font-semibold text-ink">
                <Terminal aria-hidden className="h-4 w-4 text-accent" />
                Or sign in on the mirror
              </h2>
              <p className="mb-3">Run this on the mirror, in the device folder:</p>
              <CopyBlock
                label="Register command"
                text={`python -m easyweight.register --api-url ${window.location.origin} --name "Home mirror" --email you@example.com`}
              />
            </div>
          </aside>
        )}
      </div>
    </>
  );
}
