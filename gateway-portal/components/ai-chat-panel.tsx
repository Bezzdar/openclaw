"use client"

import { useState, useRef, useCallback } from "react"
import { Bot, Send, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  SheetDescription,
} from "@/components/ui/sheet"

interface ChatMessage {
  role: "user" | "assistant"
  content: string
}

const API_BASE = process.env.NEXT_PUBLIC_RAG_API_URL || "/api"

export function AiChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isSending, setIsSending] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const sessionIdRef = useRef(`portal-${crypto.randomUUID()}`)

  const handleSend = useCallback(async () => {
    if (isSending) return

    const trimmed = input.trim()
    if (!trimmed) return

    setMessages((prev) => [...prev, { role: "user", content: trimmed }])
    setInput("")
    setIsSending(true)

    let assistantIndex = -1
    setMessages((prev) => {
      assistantIndex = prev.length + 1
      return [...prev, { role: "assistant", content: "" }]
    })

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionIdRef.current,
          message: trimmed,
        }),
      })

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""
      let currentEvent = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() || ""

        for (const rawLine of lines) {
          const line = rawLine.trimEnd()
          if (!line) continue

          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim()
            continue
          }

          if (!line.startsWith("data:")) continue
          const data = line.slice(5).trimStart()

          if (currentEvent === "token") {
            setMessages((prev) =>
              prev.map((msg, index) =>
                index === assistantIndex
                  ? { ...msg, content: msg.content + data }
                  : msg,
              ),
            )
          } else if (currentEvent === "error") {
            setMessages((prev) =>
              prev.map((msg, index) =>
                index === assistantIndex
                  ? {
                      ...msg,
                      content:
                        msg.content ||
                        "Ошибка сервера при генерации ответа. Попробуйте еще раз.",
                    }
                  : msg,
              ),
            )
            return
          } else if (currentEvent === "done") {
            return
          }
        }
      }
    } catch {
      setMessages((prev) =>
        prev.map((msg, index) =>
          index === assistantIndex
            ? {
                ...msg,
                content:
                  msg.content ||
                  "Не удалось подключиться к backend. Проверьте /api/health и nginx proxy.",
              }
            : msg,
        ),
      )
    } finally {
      setIsSending(false)
    }
  }, [input, isSending])

  const handleReset = useCallback(() => {
    setMessages([])
    setInput("")
    sessionIdRef.current = `portal-${crypto.randomUUID()}`
  }, [])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && e.shiftKey) {
        e.preventDefault()
        void handleSend()
      }
    },
    [handleSend],
  )

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="text-violet-600 hover:bg-violet-100 dark:text-violet-400 dark:hover:bg-violet-900/30"
          title="AI-Библиотекарь"
        >
          <Bot className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="flex flex-col w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-violet-600 dark:text-violet-400" />
            AI-Библиотекарь
          </SheetTitle>
          <SheetDescription>
            Задайте вопрос по документам предприятия
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto space-y-3 px-4 py-2">
          {messages.length === 0 && (
            <p className="text-sm text-muted-foreground text-center mt-8">
              Начните диалог, задав вопрос по документам предприятия.
            </p>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-violet-600 text-white"
                    : "bg-muted text-foreground"
                }`}
              >
                {msg.content || (isSending && msg.role === "assistant" ? "..." : "")}
              </div>
            </div>
          ))}
        </div>

        <div className="border-t p-4 space-y-2">
          <p className="text-xs text-muted-foreground">
            Enter - новая строка, Shift+Enter - отправить сообщение
          </p>
          <div className="flex gap-2">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Задайте вопрос..."
              className="min-h-[60px] max-h-[150px] resize-none border-violet-500/30 bg-card text-foreground placeholder:text-muted-foreground"
              rows={2}
            />
            <div className="flex flex-col gap-1">
              <Button
                variant="secondary"
                size="icon"
                onClick={() => void handleSend()}
                disabled={!input.trim() || isSending}
                className="bg-violet-200 text-violet-700 hover:bg-violet-300 dark:bg-violet-900/50 dark:text-violet-300 dark:hover:bg-violet-800/50"
                title="Отправить (Shift+Enter)"
              >
                <Send className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleReset}
                className="text-muted-foreground hover:text-foreground"
                title="Сбросить сессию"
              >
                <RotateCcw className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
