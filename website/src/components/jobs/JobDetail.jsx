"use client";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useJobAction } from "@/lib/queries";
import Link from "next/link";

const STATUS_COLOR = {
  COMPLETED: "text-green-600",
  RUNNING: "text-blue-600",
  QUEUED: "text-yellow-600",
  PENDING: "text-muted-foreground",
  FAILED: "text-red-600",
  CANCELLED: "text-muted-foreground",
  PAUSED: "text-orange-600",
};

function Field({ label, children }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </span>
      <div className="text-sm">{children}</div>
    </div>
  );
}

function JsonBlock({ data, color }) {
  const [open, setOpen] = useState(false);
  if (!data) return <span className="text-muted-foreground">—</span>;
  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
      >
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        {open ? "Hide" : "Show"}
      </button>
      {open && (
        <pre
          className={`mt-2 p-3 bg-muted rounded text-xs font-mono overflow-x-auto ${color ?? ""}`}
        >
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

export default function JobDetail({ job }) {
  const { mutate: jobAction, isPending } = useJobAction();

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="text-lg">{job.task_name}</CardTitle>
            <p className="text-xs text-muted-foreground font-mono mt-0.5">{job.id}</p>
          </div>
          <div className="flex gap-2 shrink-0">
            {["QUEUED", "RUNNING"].includes(job.status) && (
              <Button
                size="sm"
                variant="outline"
                disabled={isPending}
                onClick={() => jobAction({ id: job.id, action: "pause" })}
              >
                Pause
              </Button>
            )}
            {["PAUSED", "FAILED", "CANCELLED"].includes(job.status) && (
              <Button
                size="sm"
                variant="outline"
                disabled={isPending}
                onClick={() => jobAction({ id: job.id, action: "resume" })}
              >
                Resume
              </Button>
            )}
            {!["COMPLETED", "CANCELLED", "FAILED"].includes(job.status) && (
              <Button
                size="sm"
                variant="destructive"
                disabled={isPending}
                onClick={() => jobAction({ id: job.id, action: "cancel" })}
              >
                Cancel
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Field label="Status">
            <Badge variant="outline" className={STATUS_COLOR[job.status]}>
              {job.status}
            </Badge>
          </Field>
          <Field label="Priority">{job.priority}</Field>
          <Field label="Retries">
            {job.retry_count} / {job.max_retries}
          </Field>
        </div>

        <Field label="Progress">
          <div className="flex items-center gap-3 mt-1">
            <Progress value={job.progress * 100} className="h-2 flex-1" />
            <span className="text-sm w-10">{Math.round(job.progress * 100)}%</span>
          </div>
        </Field>

        {job.worker_id && <Field label="Worker">{job.worker_id}</Field>}

        {job.conversation_id && (
          <Field label="Conversation">
            <Link href={`/chat/${job.conversation_id}`} className="underline text-blue-600 text-xs font-mono">
              {job.conversation_id}
            </Link>
          </Field>
        )}

        <Separator />

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Field label="Created">{job.created_at ? new Date(job.created_at).toLocaleString() : "—"}</Field>
          <Field label="Started">{job.started_at ? new Date(job.started_at).toLocaleString() : "—"}</Field>
          <Field label="Finished">{job.finished_at ? new Date(job.finished_at).toLocaleString() : "—"}</Field>
        </div>

        <Separator />

        <Field label="Payload">
          <JsonBlock data={job.payload} />
        </Field>

        {job.result && (
          <Field label="Result">
            <JsonBlock data={job.result} color="text-green-700" />
          </Field>
        )}

        {job.error && (
          <Field label="Error">
            <p className="text-sm text-red-600 font-mono">{job.error}</p>
          </Field>
        )}
      </CardContent>
    </Card>
  );
}
