"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import { Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { chat, type ChatMessage } from "@/lib/api";

const EXAMPLE_PROMPTS = [
  "Who's the best professor for ECS 36C?",
  "Tell me about Professor Alexander Aue",
];

export function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSubmit = async (overrideText?: string) => {
    const text = (overrideText ?? input).trim();
    if (!text || isLoading) return;

    const userMessage: ChatMessage = { role: "user", content: text };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput("");
    setError(null);
    setIsLoading(true);

    try {
      const res = await chat(newMessages);
      setMessages(res.messages);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setMessages(newMessages);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="shrink-0 border-b border-border/50 bg-background/80 px-6 py-4 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <Image
            src="/compass.png"
            alt=""
            width={32}
            height={32}
            className="dark:invert"
          />
          <div>
            <h1 className="text-xl font-semibold">Compass AI</h1>
            <p className="text-muted-foreground text-sm">
              Ask about UC Davis professors and courses
            </p>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="flex flex-col gap-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center gap-6 py-12">
              <Image
                src="/compass.png"
                alt=""
                width={64}
                height={64}
                className="text-muted-foreground opacity-60 dark:invert dark:opacity-50"
              />
              <p className="text-muted-foreground text-center text-sm">
                Start a conversation by asking about professors or courses.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {EXAMPLE_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => handleSubmit(prompt)}
                    disabled={isLoading}
                    className="rounded-full border border-border/60 bg-muted/40 px-4 py-2 text-sm text-foreground/90 transition-colors hover:bg-muted/60 hover:border-border disabled:opacity-50"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages
            .filter(
              (msg) =>
                msg.role !== "assistant" ||
                (msg.content ?? "").trim() !== ""
            )
            .map((msg, i) => (
            <div
              key={i}
              className={cn(
                "flex",
                msg.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              {msg.role === "user" ? (
                <div className="bg-primary text-primary-foreground max-w-[85%] rounded-2xl px-4 py-2.5">
                  {msg.content}
                </div>
              ) : (
                <div className="bg-muted/50 border-border/50 max-w-[85%] rounded-2xl border px-4 py-3">
                  <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                </div>
              )}
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-muted/50 border-border/50 max-w-[85%] rounded-2xl border px-4 py-3">
                <p className="text-muted-foreground text-sm">Thinking...</p>
              </div>
            </div>
          )}
          <div ref={scrollRef} />
        </div>
      </div>

      {error && (
        <div className="shrink-0 border-t border-destructive/30 bg-destructive/10 px-6 py-2">
          <p className="text-destructive text-sm">{error}</p>
        </div>
      )}

      <div className="shrink-0 border-t border-border/50 bg-background/80 p-4 backdrop-blur-sm">
        <div className="flex gap-2">
          <Textarea
            placeholder="Ask about professors or courses..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            className="min-h-12 resize-none rounded-2xl shadow-none"
            rows={1}
          />
          <Button
            onClick={() => handleSubmit()}
            disabled={isLoading || !input.trim()}
            size="icon"
            className="h-12 shrink-0 rounded-2xl"
          >
            <Send className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
