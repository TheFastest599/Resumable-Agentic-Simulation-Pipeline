"use client";
import { useTasks } from "@/lib/queries";
import TasksGrid from "@/components/tasks/TasksGrid";
import { Skeleton } from "@/components/ui/skeleton";

export default function TasksPage() {
  const { data, isLoading } = useTasks();

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Available Tasks</h1>
        {data && (
          <span className="text-sm text-muted-foreground">{data.total} tasks</span>
        )}
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      ) : (
        <TasksGrid tasks={data?.tasks} />
      )}
    </div>
  );
}
