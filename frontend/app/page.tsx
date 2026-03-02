import { ChatInterface } from "@/components/chat/chat-interface";

export default function Home() {
  return (
    <main className="h-dvh bg-gradient-to-b from-primary via-primary/95 to-primary/90">
      <div className="mx-auto flex h-dvh min-h-0 max-w-5xl flex-col px-4 py-6 sm:px-6 lg:px-10">
        <div className="flex flex-1 min-h-0 flex-col gap-8 lg:grid lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1.3fr)] lg:items-stretch">
          <section className="flex flex-col justify-center gap-6 text-primary-foreground">
            <div className="space-y-3">
              <p className="inline-flex items-center rounded-full bg-primary-foreground/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-primary-foreground/80">
                UC Davis · Compass AI
              </p>
              <h1 className="text-balance text-3xl font-semibold leading-tight sm:text-4xl lg:text-5xl">
                Ask about UC Davis professors and courses.
              </h1>
              <p className="max-w-xl text-sm leading-relaxed text-primary-foreground/85 sm:text-base">
                A focused assistant for California&apos;s college town, built to
                help you explore instructors, classes, and academic paths at UC
                Davis with confidence.
              </p>
            </div>
          </section>

          <section className="mt-4 flex min-h-0 items-stretch lg:mt-0">
            <div className="mx-auto flex h-full min-h-0 w-full max-w-2xl flex-1 overflow-hidden rounded-2xl bg-background shadow-xl ring-1 ring-border/70">
              <ChatInterface />
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
