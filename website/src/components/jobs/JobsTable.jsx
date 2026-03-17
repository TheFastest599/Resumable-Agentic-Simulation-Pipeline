"use client";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useJobAction } from "@/lib/queries";

const STATUS_VARIANT = {
  COMPLETED: "default",
  RUNNING: "secondary",
  QUEUED: "secondary",
  PENDING: "outline",
  FAILED: "destructive",
  CANCELLED: "outline",
  PAUSED: "outline",
};

const STATUS_COLOR = {
  COMPLETED: "text-green-600",
  RUNNING: "text-blue-600",
  QUEUED: "text-yellow-600",
  PENDING: "text-muted-foreground",
  FAILED: "text-red-600",
  CANCELLED: "text-muted-foreground",
  PAUSED: "text-orange-600",
};

function StatusBadge({ status }) {
  return (
    <Badge variant={STATUS_VARIANT[status] ?? "outline"} className={STATUS_COLOR[status]}>
      {status}
    </Badge>
  );
}

const ROW_H = 57; // approximate px height per row
const SCROLL_THRESHOLD = 10;

export default function JobsTable({ jobs }) {
  const { mutate: jobAction, isPending } = useJobAction();

  if (!jobs || jobs.length === 0) {
    return <p className="text-sm text-muted-foreground py-8 text-center">No jobs found.</p>;
  }

  const scrollable = jobs.length > SCROLL_THRESHOLD;

  return (
    <div className={scrollable ? "rounded-md border overflow-hidden" : undefined}>
      <div
        className={scrollable ? "overflow-y-auto" : undefined}
        style={scrollable ? { maxHeight: SCROLL_THRESHOLD * ROW_H } : undefined}
      >
      <Table>
        <TableHeader className={scrollable ? "sticky top-0 bg-background z-10" : undefined}>
          <TableRow>
            <TableHead>Task</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="w-32">Progress</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
        {jobs.map((job) => (
          <TableRow key={job.id} className="hover:bg-muted/50">
            <TableCell>
              <Link href={`/jobs/${job.id}`} className="font-medium hover:underline">
                {job.task_name}
              </Link>
              <p className="text-xs text-muted-foreground font-mono truncate max-w-45">
                {job.id}
              </p>
            </TableCell>
            <TableCell>
              <StatusBadge status={job.status} />
            </TableCell>
            <TableCell>
              <div className="flex items-center gap-2">
                <Progress value={job.progress * 100} className="h-1.5 w-20" />
                <span className="text-xs text-muted-foreground w-8">
                  {Math.round(job.progress * 100)}%
                </span>
              </div>
            </TableCell>
            <TableCell className="text-sm text-muted-foreground">
              {new Date(job.created_at).toLocaleString()}
            </TableCell>
            <TableCell className="text-right">
              <div className="flex gap-1 justify-end">
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
            </TableCell>
          </TableRow>
        ))}
        </TableBody>
      </Table>
      </div>
    </div>
  );
}
