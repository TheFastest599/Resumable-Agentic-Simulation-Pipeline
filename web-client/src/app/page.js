import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  BrainCircuit,
  FlaskConical,
  Layers,
  Workflow,
  Zap,
  ShieldCheck,
  ArrowRight,
} from "lucide-react";

const features = [
  {
    icon: BrainCircuit,
    title: "LLM Agent",
    desc: "Natural language interface powered by Groq running openai/gpt-oss-120b. Describe what you need — the agent submits, monitors, and chains jobs automatically.",
  },
  {
    icon: FlaskConical,
    title: "30 Simulation Tasks",
    desc: "Monte Carlo, heat diffusion, fluid dynamics, linear algebra, physics, epidemics, cellular automata, and more.",
  },
  {
    icon: Workflow,
    title: "DAG Workflows",
    desc: "Chain simulations with dependencies. Job B waits for Job A to complete before it starts — all expressed in plain language.",
  },
  {
    icon: Zap,
    title: "Real-time Streaming",
    desc: "Watch the agent think token by token via SSE. Tool calls appear as live indicators while work is in flight.",
  },
  {
    icon: Layers,
    title: "Priority Queue",
    desc: "Redis-backed sorted-set queue with configurable priority 1–10 and anti-starvation age boosting.",
  },
  {
    icon: ShieldCheck,
    title: "Resilient Workers",
    desc: "Heartbeat leases, zombie recovery, exponential backoff retries, pause/resume, and orphan healing via scheduler.",
  },
];

const stack = [
  "FastAPI", "PostgreSQL", "Redis / Memurai", "SQLAlchemy 2.0",
  "LangChain", "Groq API", "openai/gpt-oss-120b", "Next.js 15", "TanStack Query", "Zustand",
];

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-6 py-24 border-b">
        <Badge variant="outline" className="mb-4 text-xs tracking-wider">
          Resumable Agentic Simulation Pipeline
        </Badge>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-4">RASP</h1>
        <p className="text-muted-foreground text-lg max-w-xl mb-8">
          A distributed scientific simulation engine with an LLM agent front-end.
          Describe your experiment in plain language — RASP handles the rest.
        </p>
        <div className="flex gap-3 flex-wrap justify-center">
          <Button asChild size="lg">
            <Link href="/chat">
              Start chatting <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/tasks">Browse tasks</Link>
          </Button>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 py-16 max-w-5xl mx-auto w-full">
        <h2 className="text-xl font-semibold mb-8 text-center">What it does</h2>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="flex gap-4 p-4 rounded-lg border bg-card">
              <div className="shrink-0 mt-0.5">
                <Icon className="h-5 w-5 text-muted-foreground" />
              </div>
              <div>
                <p className="font-medium text-sm mb-1">{title}</p>
                <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <Separator />

      {/* Stack */}
      <section className="px-6 py-10 max-w-5xl mx-auto w-full">
        <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-4 text-center">
          Built with
        </h2>
        <div className="flex flex-wrap gap-2 justify-center">
          {stack.map((s) => (
            <Badge key={s} variant="secondary" className="text-xs">
              {s}
            </Badge>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t px-6 py-4 text-center text-xs text-muted-foreground">
        RASP · Resumable Agentic Simulation Pipeline
      </footer>
    </div>
  );
}
