"use client";
import { use } from "react";
import { useJob } from "@/lib/queries";
import JobDetail from "@/components/jobs/JobDetail";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, RefreshCw } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useQueryClient } from "@tanstack/react-query";

export default function JobDetailPage({ params }) {
  const { id } = use(params);
  const qc = useQueryClient();
  const { data: job, isLoading, isFetching, error } = useJob(id);

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/jobs">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Jobs
          </Link>
        </Button>
        <Button
          size="icon"
          variant="ghost"
          disabled={isFetching}
          onClick={() => qc.invalidateQueries({ queryKey: ["job", id] })}
          title="Refresh"
        >
          <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      )}

      {error && (
        <p className="text-red-600 text-sm">Failed to load job: {error.message}</p>
      )}

      {job && <JobDetail job={job} />}
    </div>
  );
}
