import { useState } from "react";
import type { FormEvent } from "react";

import type { DeviceCreated } from "../api/types";
import { useAddDevice, useDevices, useRemoveDevice } from "../api/queries";
import { useAuth } from "../auth/AuthContext";
import { EmptyState, ErrorNote, PageHeader, Spinner } from "../components/ui";
import { formatAgo, formatDate } from "../lib/format";

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
            <EmptyState title="No mirrors yet">Add your first mirror with the form.</EmptyState>
          ) : (
            <ul className="card divide-y divide-line">
              {devices.data.map((d) => (
                <li
                  key={d.id}
                  className="flex flex-wrap items-center justify-between gap-3 px-5 py-4"
                >
                  <div>
                    <div className="font-medium">{d.name}</div>
                    <div className="text-sm text-muted">
                      {d.last_seen_at
                        ? `Last sent ${formatAgo(d.last_seen_at)}`
                        : "Hasn't sent anything yet"}
                      <span className="text-faint"> · added {formatDate(d.created_at)}</span>
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
                      Remove
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        {readOnly ? (
          <aside className="card h-fit p-5 text-sm text-muted">
            <h2 className="mb-2 font-semibold text-ink">This is the demo</h2>
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
            <div className="card p-5 text-sm text-muted">
              <h2 className="mb-2 font-semibold text-ink">Or from the mirror itself</h2>
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
