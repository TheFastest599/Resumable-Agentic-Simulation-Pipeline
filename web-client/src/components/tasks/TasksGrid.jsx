"use client";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MessageSquare } from "lucide-react";
import useChatStore from "@/store/chatStore";

export default function TasksGrid({ tasks }) {
  const router = useRouter();
  const { setMessages, setActiveConvId } = useChatStore();

  const askAbout = (task) => {
    setMessages([]);
    setActiveConvId(null);
    // Navigate to /chat with a prefilled message stored in sessionStorage
    sessionStorage.setItem(
      "prefill",
      `Run a ${task.name} simulation with default parameters.`
    );
    router.push("/chat");
  };

  if (!tasks || tasks.length === 0) {
    return <p className="text-muted-foreground text-sm">No tasks available.</p>;
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {tasks.map((task) => (
        <Card key={task.name} className="flex flex-col">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-mono">{task.name}</CardTitle>
            <p className="text-xs text-muted-foreground">{task.description}</p>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col justify-between gap-3">
            <pre className="bg-muted rounded p-2 text-xs font-mono overflow-x-auto whitespace-pre-wrap">
              {JSON.stringify(task.default_payload, null, 2)}
            </pre>
            <Button size="sm" variant="outline" onClick={() => askAbout(task)}>
              <MessageSquare className="h-3.5 w-3.5 mr-1.5" />
              Ask agent
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
