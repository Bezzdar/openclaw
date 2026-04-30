"use client"

import { useEffect, useState } from "react"
import { Moon, Sun } from "lucide-react"
import { Button } from "@/components/ui/button"
import { AiChatPanel } from "@/components/ai-chat-panel"

export function Header() {
  // Добавляем флаг, чтобы знать, когда компонент смонтирован на клиенте
  const [mounted, setMounted] = useState(false)
  const [currentTime, setCurrentTime] = useState(new Date())
  const [isDark, setIsDark] = useState(true)

  useEffect(() => {
    // Устанавливаем флаг mounted в true только на клиенте
    setMounted(true)
    
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    const root = document.documentElement
    if (isDark) {
      root.classList.add("dark")
    } else {
      root.classList.remove("dark")
    }
  }, [isDark])

  const formatDateTime = (date: Date) => {
    const day = date.getDate()
    const months = [
      "Января", "Февраля", "Марта", "Апреля", "Мая", "Июня",
      "Июля", "Августа", "Сентября", "Октября", "Ноября", "Декабря"
    ]
    const month = months[date.getMonth()]
    const year = date.getFullYear()
    const time = date.toLocaleTimeString("ru-RU", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    })
    return `${day} ${month} ${year}, ${time}`
  }

  return (
    <header className="flex h-14 items-center justify-between border-b border-border px-6 bg-background">
      <h1 className="text-xl font-bold text-foreground">
        Корпоративный портал ИХТЦ
      </h1>
      
      <div className="text-sm font-medium tabular-nums text-foreground">
        {/* Если компонент смонтирован (браузер) — показываем время.
           Если нет (сервер) — показываем невидимую заглушку той же ширины,
           чтобы избежать ошибки гидратации и дергания интерфейса.
        */}
        {mounted ? (
          formatDateTime(currentTime)
        ) : (
          <span className="opacity-0">00 Января 0000, 00:00:00</span>
        )}
      </div>
      
      <div className="flex items-center gap-1">
        <AiChatPanel />
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setIsDark(!isDark)}
          className="text-foreground hover:bg-accent"
        >
          {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </Button>
      </div>
    </header>
  )
}
