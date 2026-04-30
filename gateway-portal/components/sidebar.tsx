"use client"

import { useState } from "react"
import Link from "next/link"
import {
  Globe,
  FolderKanban,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Network,
  Handshake,
  Rocket,
  ClipboardList
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const navigationLinks = [
  {
    title: "Сайт",
    href: "https://ect-center.com/",
    icon: Globe,
  },
  {
    title: "OpenProject",
    href: "http://10.0.10.155:8080/",
    icon: FolderKanban,
  },
  {
    title: "Википедия ИХТЦ",
    href: "http://10.0.10.157:3000/",
    icon: BookOpen,
  },
]

const internalLinks = [
  {
    title: "Структура компании",
    href: "#",
    icon: Network,
  },
  {
    title: "Работа с партнерами",
    href: "#",
    icon: Handshake,
  },
  {
    title: "Первый день в ИХТЦ",
    href: "#",
    icon: Rocket,
  },
  {
    title: "Реестр проектов",
    href: "#",
    icon: ClipboardList,
  },
  // ────────────────────────────────────────────────────────────
  // Шаблон для добавления новой ссылки в блок «Быстрые ссылки»:
  //
  // {
  //   title: "Название ссылки",        // Текст, отображаемый в меню
  //   href: "https://example.com/",    // URL-адрес ссылки
  //   icon: Network,                   // Иконка из lucide-react (https://lucide.dev/icons)
  //                                    // Импортируйте нужную иконку вверху файла:
  //                                    // import { ИмяИконки } from "lucide-react"
  // },
  // ────────────────────────────────────────────────────────────
]

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={cn(
        "relative flex h-full flex-col border-r border-border bg-sidebar transition-all duration-300",
        collapsed ? "w-16" : "w-64",
      )}
    >
      <div className="flex h-14 items-center justify-between border-b border-sidebar-border px-4">
        {!collapsed && (
          <span className="text-lg font-bold text-sidebar-foreground">ИХТЦ</span>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setCollapsed(!collapsed)}
          className="ml-auto text-sidebar-foreground hover:bg-sidebar-accent"
        >
          {collapsed ? <ChevronRight className="h-5 w-5" /> : <ChevronLeft className="h-5 w-5" />}
        </Button>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        {navigationLinks.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sidebar-foreground transition-colors hover:bg-sidebar-accent",
              collapsed && "justify-center",
            )}
          >
            <link.icon className="h-5 w-5 flex-shrink-0" />
            {!collapsed && <span>{link.title}</span>}
          </Link>
        ))}

        {!collapsed && (
          <div className="pt-4">
            {internalLinks.map((link) => (
              <Link
                key={link.title}
                href={link.href}
                className="flex items-center gap-3 rounded-lg px-3 py-2 text-sidebar-foreground transition-colors hover:bg-sidebar-accent"
              >
                <link.icon className="h-5 w-5 flex-shrink-0" />
                <span>{link.title}</span>
              </Link>
            ))}
          </div>
        )}

        {collapsed && (
          <div className="pt-4 flex flex-col items-center gap-2">
            {internalLinks.map((link) => (
              <Link
                key={link.title}
                href={link.href}
                className="flex items-center justify-center rounded-lg p-2 text-sidebar-foreground transition-colors hover:bg-sidebar-accent"
                title={link.title}
              >
                <link.icon className="h-5 w-5" />
              </Link>
            ))}
          </div>
        )}
      </nav>
    </aside>
  )
}
