import { ChatInterface } from "@/components/chat/chat-interface";

export default function Home() {
  return (
    <main className="bg-muted/20 mx-auto flex h-dvh max-w-2xl flex-col overflow-hidden rounded-none sm:my-4 sm:max-h-[calc(100dvh-2rem)] sm:rounded-xl sm:border sm:border-border/50 sm:bg-background">
      <ChatInterface />
    </main>
  );
}
