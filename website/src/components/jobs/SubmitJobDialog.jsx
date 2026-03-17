"use client";
import { useState, useEffect } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useTasks, useSubmitJob } from "@/lib/queries";
import { toast } from "sonner";

export default function SubmitJobDialog() {
  const [open, setOpen] = useState(false);
  const { data: tasksData } = useTasks();
  const tasks = tasksData?.tasks ?? [];

  const [taskName, setTaskName] = useState("");
  const [payload, setPayload] = useState("{}");
  const [priority, setPriority] = useState("5");
  const [payloadError, setPayloadError] = useState("");

  const { mutate: submit, isPending } = useSubmitJob();

  // Pre-fill payload when task changes
  useEffect(() => {
    const t = tasks.find((t) => t.name === taskName);
    if (t) setPayload(JSON.stringify(t.default_payload, null, 2));
  }, [taskName, tasks]);

  const handleSubmit = () => {
    let parsed;
    try {
      parsed = JSON.parse(payload);
    } catch {
      setPayloadError("Invalid JSON");
      return;
    }
    setPayloadError("");
    submit(
      { task_name: taskName, payload: parsed, priority: Number(priority) },
      {
        onSuccess: (job) => {
          toast.success(`Job submitted — ${job.id}`);
          setOpen(false);
          setTaskName("");
          setPayload("{}");
          setPriority("5");
        },
        onError: (err) => toast.error(err.message ?? "Submit failed"),
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="h-4 w-4 mr-1.5" />
          New Job
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Submit a Job</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 pt-2">
          {/* Task */}
          <div className="space-y-1.5">
            <Label>Task</Label>
            <Select value={taskName} onValueChange={setTaskName}>
              <SelectTrigger>
                <SelectValue placeholder="Select a task…" />
              </SelectTrigger>
              <SelectContent className="max-h-64">
                {tasks.map((t) => (
                  <SelectItem key={t.name} value={t.name}>
                    <span className="font-mono text-sm">{t.name}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Payload */}
          <div className="space-y-1.5">
            <Label>Payload (JSON)</Label>
            <Textarea
              value={payload}
              onChange={(e) => { setPayload(e.target.value); setPayloadError(""); }}
              className="font-mono text-xs min-h-28 resize-none"
            />
            {payloadError && (
              <p className="text-xs text-red-500">{payloadError}</p>
            )}
          </div>

          {/* Priority */}
          <div className="space-y-1.5">
            <Label>Priority (1 = low, 10 = high)</Label>
            <Input
              type="number"
              min={1}
              max={10}
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="w-24"
            />
          </div>

          <Button
            className="w-full"
            disabled={!taskName || isPending}
            onClick={handleSubmit}
          >
            {isPending ? "Submitting…" : "Submit"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
