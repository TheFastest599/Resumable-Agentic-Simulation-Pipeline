"use client";
import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ChevronLeft, ChevronRight, RefreshCw } from "lucide-react";
import JobsTable from "@/components/jobs/JobsTable";
import SubmitJobDialog from "@/components/jobs/SubmitJobDialog";
import { useJobs } from "@/lib/queries";
import { useQueryClient } from "@tanstack/react-query";

const STATUSES = [
	"ALL",
	"QUEUED",
	"PENDING",
	"RUNNING",
	"COMPLETED",
	"FAILED",
	"PAUSED",
	"CANCELLED",
];
const PAGE_SIZE = 20;

function JobsContent() {
	const searchParams = useSearchParams();
	const [status, setStatus] = useState("ALL");
	const [convId, setConvId] = useState(
		searchParams.get("conversation_id") ?? "",
	);
	const [page, setPage] = useState(1);

	const qc = useQueryClient();
	const { data, isLoading, isFetching } = useJobs(
		status === "ALL" ? undefined : status,
		convId.trim() || undefined,
		page,
	);

	const total = data?.total ?? 0;
	const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

	// Reset to page 1 when filters change
	const handleStatusChange = (v) => {
		setStatus(v);
		setPage(1);
	};
	const handleConvChange = (e) => {
		setConvId(e.target.value);
		setPage(1);
	};

	return (
		<div className="p-6 max-w-6xl mx-auto space-y-4">
			<div className="flex items-center justify-between">
				<h1 className="text-xl font-semibold">Jobs</h1>
				<div className="flex items-center gap-2">
					<Button
						size="icon"
						variant="ghost"
						disabled={isFetching}
						onClick={() =>
							qc.invalidateQueries({ queryKey: ["jobs"] })
						}
						title="Refresh"
					>
						<RefreshCw
							className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`}
						/>
					</Button>
					<SubmitJobDialog />
				</div>
			</div>

			<div className="flex gap-3 flex-wrap">
				<Select value={status} onValueChange={handleStatusChange}>
					<SelectTrigger className="w-40">
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						{STATUSES.map((s) => (
							<SelectItem key={s} value={s}>
								{s}
							</SelectItem>
						))}
					</SelectContent>
				</Select>

				<Input
					placeholder="Filter by conversation ID…"
					value={convId}
					onChange={handleConvChange}
					className="w-80 font-mono text-sm"
				/>
			</div>

			{isLoading ? (
				<div className="space-y-2">
					{[...Array(5)].map((_, i) => (
						<Skeleton key={i} className="h-12 w-full" />
					))}
				</div>
			) : (
				<JobsTable jobs={data?.jobs} />
			)}

			{/* Pagination */}
			<div className="flex items-center justify-between pt-2">
				<p className="text-sm text-muted-foreground">
					{total === 0
						? "No jobs"
						: `${(page - 1) * PAGE_SIZE + 1}–${Math.min(page * PAGE_SIZE, total)} of ${total}`}
				</p>
				<div className="flex items-center gap-2">
					<Button
						variant="outline"
						size="icon"
						disabled={page === 1 || isLoading}
						onClick={() => setPage((p) => p - 1)}
					>
						<ChevronLeft className="h-4 w-4" />
					</Button>
					<span className="text-sm w-20 text-center">
						Page {page} of {totalPages}
					</span>
					<Button
						variant="outline"
						size="icon"
						disabled={page >= totalPages || isLoading}
						onClick={() => setPage((p) => p + 1)}
					>
						<ChevronRight className="h-4 w-4" />
					</Button>
				</div>
			</div>
		</div>
	);
}

export default function JobsPage() {
	return (
		<Suspense>
			<JobsContent />
		</Suspense>
	);
}
