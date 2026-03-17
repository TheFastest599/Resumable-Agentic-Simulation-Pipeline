"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/sonner";
import { useState } from "react";

export default function Providers({ children }) {
  const [qc] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={qc}>
      {children}
      <Toaster />
    </QueryClientProvider>
  );
}
