"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import { Send } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { createPortal } from "react-dom";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { chat, type ChatMessage } from "@/lib/api";

type UIMessage = ChatMessage & { id: string };

function makeId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`;
}

function normalizeContent(content: string) {
  return content.trim();
}

function reconcileMessages(prev: UIMessage[], next: ChatMessage[]): UIMessage[] {
  return next.map((msg, idx) => {
    const prevMsg = prev[idx];
    if (
      prevMsg &&
      prevMsg.role === msg.role &&
      normalizeContent(prevMsg.content) === normalizeContent(msg.content)
    ) {
      return { ...prevMsg, content: msg.content };
    }
    return { ...msg, id: makeId() };
  });
}

type Rect = Pick<DOMRect, "left" | "top" | "width" | "height">;

function rectFromDomRect(rect: DOMRect): Rect {
  return {
    left: rect.left,
    top: rect.top,
    width: rect.width,
    height: rect.height,
  };
}

const EXAMPLE_PROMPTS = [
  "Who's the best professor for ECS 36C?",
  "Tell me about Professor Alexander Aue",
];

export function ChatInterface() {
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const bubbleRefs = useRef(new Map<string, HTMLDivElement>());
  const shouldReduceMotion = useReducedMotion();
  const [isMounted, setIsMounted] = useState(false);

  const [hiddenMessageIds, setHiddenMessageIds] = useState<Set<string>>(
    () => new Set()
  );
  const [sendOverlay, setSendOverlay] = useState<{
    messageId: string;
    content: string;
    from: Rect;
    to: Rect;
  } | null>(null);
  const pendingSendRef = useRef<{
    messageId: string;
    content: string;
    fromRect: Rect;
  } | null>(null);
  const animatingRef = useRef(false);

  const scrollToBottom = useCallback(() => {
    scrollRef.current?.scrollIntoView({
      behavior: animatingRef.current ? "instant" : "smooth",
    });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (shouldReduceMotion) {
      pendingSendRef.current = null;
      setSendOverlay(null);
      setHiddenMessageIds(new Set());
    }
  }, [shouldReduceMotion]);

  useEffect(() => {
    if (shouldReduceMotion) return;
    if (sendOverlay) return;
    const pending = pendingSendRef.current;
    if (!pending) return;

    const raf = requestAnimationFrame(() => {
      const bubbleEl = bubbleRefs.current.get(pending.messageId);
      if (!bubbleEl) return;

      const toRect = rectFromDomRect(bubbleEl.getBoundingClientRect());
      const startLeft = pending.fromRect.left + pending.fromRect.width - toRect.width;
      const startTop =
        pending.fromRect.top + (pending.fromRect.height - toRect.height) / 2;
      const fromRect: Rect = {
        left: startLeft,
        top: startTop,
        width: toRect.width,
        height: toRect.height,
      };

      setSendOverlay({
        messageId: pending.messageId,
        content: pending.content,
        from: fromRect,
        to: toRect,
      });
      pendingSendRef.current = null;
    });

    return () => cancelAnimationFrame(raf);
  }, [messages, sendOverlay, shouldReduceMotion]);

  const handleSubmit = async (overrideText?: string) => {
    const text = (overrideText ?? input).trim();
    if (!text || isLoading) return;

    const userMessage: UIMessage = { id: makeId(), role: "user", content: text };
    const newMessages: UIMessage[] = [...messages, userMessage];
    setMessages(newMessages);
    setInput("");
    setError(null);
    setIsLoading(true);

    if (!shouldReduceMotion) {
      const fromEl = textareaRef.current;
      if (fromEl) {
        animatingRef.current = true;
        pendingSendRef.current = {
          messageId: userMessage.id,
          content: userMessage.content,
          fromRect: rectFromDomRect(fromEl.getBoundingClientRect()),
        };
        setHiddenMessageIds((prev) => {
          const next = new Set(prev);
          next.add(userMessage.id);
          return next;
        });
      }
    }

    const outgoingMessages: ChatMessage[] = newMessages.map(({ role, content }) => ({
      role,
      content,
    }));

    try {
      const res = await chat(outgoingMessages);
      setMessages((prev) => reconcileMessages(prev, res.messages));
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
    <div className="flex h-full min-h-0 w-full flex-col">
      <header className="shrink-0 border-b border-primary/40 bg-primary px-6 py-4 text-primary-foreground shadow-sm">
        <div className="flex flex-col gap-3">
          <div
            className="flex items-center gap-2"
            aria-hidden="true"
          >
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#ff605c] ring-1 ring-black/20 sm:h-3 sm:w-3" />
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#ffbd44] ring-1 ring-black/20 sm:h-3 sm:w-3" />
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#00ca4e] ring-1 ring-black/20 sm:h-3 sm:w-3" />
          </div>
          <div className="flex items-center gap-4">
            <Image
              src="/aggie.png"
              alt="UC Davis Aggies logo"
              width={64}
              height={40}
              className="h-10 w-10"
            />
            <div>
              <h1 className="text-xl font-semibold tracking-tight">
                Compass AI
              </h1>
              <p className="text-sm text-primary-foreground/80">
                Ask about UC Davis professors and courses
              </p>
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="flex flex-col gap-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center gap-6 py-12">
              <Image
                src="/uc_davis.png"
                alt="UC Davis wordmark"
                width={164}
                height={164}
                className="opacity-90"
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
                    className="rounded-full border border-accent/30 bg-background/80 px-4 py-2 text-sm text-primary/90 shadow-xs transition-colors hover:border-accent/60 hover:bg-accent/10 disabled:opacity-50"
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
                msg.content.trim() !== ""
            )
            .map((msg) => (
              <div
                key={msg.id}
                className={cn(
                  "flex",
                  msg.role === "user" ? "justify-end" : "justify-start"
                )}
              >
                {msg.role === "user" ? (
                  <div
                    ref={(el) => {
                      if (!el) {
                        bubbleRefs.current.delete(msg.id);
                        return;
                      }
                      bubbleRefs.current.set(msg.id, el);
                    }}
                    className={cn(
                      "bg-primary text-primary-foreground max-w-[85%] rounded-3xl px-4 py-2.5 shadow-sm",
                      hiddenMessageIds.has(msg.id) && "opacity-0"
                    )}
                  >
                    {msg.content}
                  </div>
                ) : (
                  shouldReduceMotion ? (
                    <div className="bg-card max-w-[85%] rounded-3xl border border-border/70 px-4 py-3 shadow-xs">
                      <p className="whitespace-pre-wrap text-sm leading-relaxed">
                        {msg.content}
                      </p>
                    </div>
                  ) : (
                    <motion.div
                      className="bg-card max-w-[85%] rounded-3xl border border-border/70 px-4 py-3 shadow-xs"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                    >
                      <p className="whitespace-pre-wrap text-sm leading-relaxed">
                        {msg.content}
                      </p>
                    </motion.div>
                  )
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

      {!shouldReduceMotion &&
        isMounted &&
        sendOverlay &&
        createPortal(
          <motion.div
            aria-hidden="true"
            className="bg-primary text-primary-foreground pointer-events-none fixed z-50 max-w-[85vw] rounded-3xl px-4 py-2.5 shadow-sm"
            style={{
              left: sendOverlay.from.left,
              top: sendOverlay.from.top,
              width: sendOverlay.from.width,
            }}
            initial={{ x: 0, y: 0, scale: 1, opacity: 1 }}
            animate={{
              x: sendOverlay.to.left - sendOverlay.from.left,
              y: sendOverlay.to.top - sendOverlay.from.top,
              scale: 1,
            }}
            transition={{
              duration: 0.45,
              ease: [0.16, 1, 0.3, 1],
            }}
            onAnimationComplete={() => {
              animatingRef.current = false;
              setHiddenMessageIds((prev) => {
                const next = new Set(prev);
                next.delete(sendOverlay.messageId);
                return next;
              });
              setSendOverlay(null);
            }}
          >
            {sendOverlay.content}
          </motion.div>,
          document.body
        )}

      {error && (
        <div className="shrink-0 border-t border-destructive/30 bg-destructive/10 px-6 py-2">
          <p className="text-destructive text-sm">{error}</p>
        </div>
      )}

      <div className="shrink-0 border-t border-border/50 bg-background/80 p-4 backdrop-blur-sm">
        <div className="flex gap-2">
          <Textarea
            ref={textareaRef}
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
