"use client";
import { useEffect } from "react";
import { use } from "react";
import Link from "next/link";
import { Briefcase } from "lucide-react";
import { Button } from "@/components/ui/button";
import ChatPanel from "@/components/chat/ChatPanel";
import { useConversation } from "@/lib/queries";
import useChatStore from "@/store/chatStore";
import { Skeleton } from "@/components/ui/skeleton";

export default function ConversationPage({ params }) {
	const { id } = use(params);
	const { data, isLoading } = useConversation(id);
	const { setMessages, setActiveConvId, activeConvId } = useChatStore();

	useEffect(() => {
		if (data && activeConvId !== id) {
			setActiveConvId(id);
			const msgs = (data.messages ?? []).map((m) => ({
				id: m.id,
				role: m.role,
				content: m.text,
			}));
			setMessages(msgs);
		}
	}, [data, id, activeConvId, setActiveConvId, setMessages]);

	if (isLoading) {
		return (
			<div className="p-6 space-y-3 max-w-3xl mx-auto">
				<Skeleton className="h-10 w-full" />
				<Skeleton className="h-10 w-3/4" />
				<Skeleton className="h-10 w-full" />
			</div>
		);
	}

	return (
		<div className="relative h-full">
			<Button
				asChild
				size="sm"
				variant="outline"
				className="absolute top-3 right-6 z-10 gap-1.5 text-xs"
			>
				<Link href={`/jobs?conversation_id=${id}`}>
					<Briefcase className="h-3.5 w-3.5" />
					List Jobs
				</Link>
			</Button>
			<ChatPanel conversationId={id} />
		</div>
	);
}
