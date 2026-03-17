"use client";
import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Plus, MessageSquare, Briefcase, FlaskConical, Trash2, Home, Pencil, Check, X, ChevronsUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useConversations, useDeleteConversation, useRenameConversation } from "@/lib/queries";
import useChatStore from "@/store/chatStore";

function NavLink({ href, icon: Icon, label, exact = false }) {
  const pathname = usePathname();
  const active = exact ? pathname === href : pathname.startsWith(href);
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors",
        active
          ? "bg-accent text-accent-foreground font-medium"
          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {label}
    </Link>
  );
}

function ConversationItem({ conv, active, onDelete, onRename }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(conv.name || "");
  const inputRef = useRef(null);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const startEdit = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setValue(conv.name || "");
    setEditing(true);
  };

  const commitEdit = (e) => {
    e?.preventDefault();
    e?.stopPropagation();
    const trimmed = value.trim();
    if (trimmed && trimmed !== conv.name) onRename(conv.id, trimmed);
    setEditing(false);
  };

  const cancelEdit = (e) => {
    e?.stopPropagation();
    setEditing(false);
  };

  if (editing) {
    return (
      <div className="flex items-center gap-1 px-2 py-1 rounded-md bg-accent">
        <MessageSquare className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        <Input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") commitEdit(e);
            if (e.key === "Escape") cancelEdit(e);
          }}
          className="h-6 text-xs px-1 border-0 shadow-none focus-visible:ring-0 bg-transparent"
          onClick={(e) => e.stopPropagation()}
        />
        <button onClick={commitEdit} className="shrink-0 text-green-600 hover:text-green-700">
          <Check className="h-3.5 w-3.5" />
        </button>
        <button onClick={cancelEdit} className="shrink-0 text-muted-foreground hover:text-foreground">
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    );
  }

  return (
    <Link
      href={`/chat/${conv.id}`}
      className={cn(
        "flex items-center justify-between gap-1 px-3 py-2 rounded-md text-sm group transition-colors",
        active
          ? "bg-accent text-accent-foreground"
          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
      )}
    >
      <span className="flex items-center gap-2 truncate">
        <MessageSquare className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">{conv.name || "Untitled"}</span>
      </span>
      <span className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
        <button
          onClick={startEdit}
          className="hover:text-foreground p-0.5 rounded"
          title="Rename"
        >
          <Pencil className="h-3 w-3" />
        </button>
        <button
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); onDelete(conv.id); }}
          className="hover:text-destructive p-0.5 rounded"
          title="Delete"
        >
          <Trash2 className="h-3 w-3" />
        </button>
      </span>
    </Link>
  );
}

const CONV_PAGE = 20;

export default function AppSidebar() {
  const { data: conversations } = useConversations();
  const deleteMutation = useDeleteConversation();
  const renameMutation = useRenameConversation();
  const pathname = usePathname();
  const router = useRouter();
  const { setMessages, setActiveConvId } = useChatStore();
  const [visibleCount, setVisibleCount] = useState(CONV_PAGE);

  const handleNewChat = () => {
    setMessages([]);
    setActiveConvId(null);
    router.push("/chat");
  };

  const handleDelete = (id) => {
    deleteMutation.mutate(id);
    if (pathname === `/chat/${id}`) router.push("/chat");
  };

  const handleRename = (id, name) => {
    renameMutation.mutate({ id, name });
  };

  return (
    <aside className="w-64 shrink-0 border-r flex flex-col h-screen bg-background">
      {/* Header */}
      <div className="px-4 py-4 flex items-center justify-between">
        <span className="font-semibold text-sm tracking-tight">RASP</span>
        <Button size="icon" variant="ghost" onClick={handleNewChat} title="New chat">
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      <Separator />

      {/* Nav */}
      <div className="px-2 py-2 space-y-1">
        <NavLink href="/" icon={Home} label="Home" exact />
        <NavLink href="/jobs" icon={Briefcase} label="Jobs" />
        <NavLink href="/tasks" icon={FlaskConical} label="Tasks" />
      </div>

      <Separator />

      {/* Conversations */}
      <div className="px-3 py-2">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
          Conversations
        </p>
      </div>

      <ScrollArea className="flex-1 px-2">
        {!conversations || conversations.length === 0 ? (
          <p className="text-xs text-muted-foreground px-3 py-2">No conversations yet</p>
        ) : (
          <div className="space-y-0.5 pb-2">
            {conversations.slice(0, visibleCount).map((conv) => (
              <ConversationItem
                key={conv.id}
                conv={conv}
                active={pathname === `/chat/${conv.id}`}
                onDelete={handleDelete}
                onRename={handleRename}
              />
            ))}
            {visibleCount < conversations.length && (
              <button
                onClick={() => setVisibleCount((n) => n + CONV_PAGE)}
                className="w-full flex items-center justify-center gap-1 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-accent rounded-md transition-colors"
              >
                <ChevronsUpDown className="h-3 w-3" />
                Show more ({conversations.length - visibleCount} remaining)
              </button>
            )}
          </div>
        )}
      </ScrollArea>
    </aside>
  );
}
