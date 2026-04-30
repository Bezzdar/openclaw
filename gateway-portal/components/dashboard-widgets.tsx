"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AlertCircle, Cake } from "lucide-react"
import { useEffect, useState } from "react"

interface Announcement {
  active: boolean
  message: string
}

interface Birthday {
  name: string
  date: string
  position: string
  company: string
}

// Parse DD.MM.YYYY date format
function parseBirthdayDate(dateStr: string): Date | null {
  const parts = dateStr.split(".")
  if (parts.length !== 3) return null
  const day = Number.parseInt(parts[0], 10)
  const month = Number.parseInt(parts[1], 10) - 1 // Month is 0-indexed
  const year = Number.parseInt(parts[2], 10)
  if (Number.isNaN(day) || Number.isNaN(month) || Number.isNaN(year)) return null
  return new Date(year, month, day)
}

// Format date as "DD month" in Russian
function formatBirthdayDisplay(dateStr: string): string {
  const date = parseBirthdayDate(dateStr)
  if (!date) return dateStr
  return date.toLocaleDateString("ru-RU", { day: "numeric", month: "long" })
}

export function DashboardWidgets() {
  const [announcement, setAnnouncement] = useState<Announcement | null>(null)
  const [birthdays, setBirthdays] = useState<Birthday[]>([])
  const [upcomingBirthdays, setUpcomingBirthdays] = useState<Birthday[]>([])

  useEffect(() => {
    // Fetch announcements
    fetch("/data/announcements.json")
      .then((res) => res.json())
      .then((data) => setAnnouncement(data))
      .catch(() => setAnnouncement({ active: false, message: "" }))

    // Fetch and parse birthdays CSV (semicolon-separated: name;position;company;date)
    fetch("/data/birthdays.csv")
      .then((res) => res.text())
      .then((text) => {
        const lines = text.trim().split("\n")
        // Skip header line
        const data = lines.slice(1).map((line) => {
          const values = line.split(";")
          return {
            name: values[0]?.trim() || "",
            position: values[1]?.trim() || "",
            company: values[2]?.trim() || "",
            date: values[3]?.trim() || "",
          }
        }).filter(b => b.name && b.date) // Filter out empty rows
        setBirthdays(data)
      })
      .catch(() => setBirthdays([]))
  }, [])

  useEffect(() => {
    if (birthdays.length === 0) return

    const today = new Date()
    today.setHours(0, 0, 0, 0)

    const eightDaysLater = new Date(today)
    eightDaysLater.setDate(today.getDate() + 8)

    const upcoming = birthdays.filter((b) => {
      const bDate = parseBirthdayDate(b.date)
      if (!bDate) return false

      // Set the birthday to the current year for comparison
      bDate.setFullYear(today.getFullYear())
      bDate.setHours(0, 0, 0, 0)

      return bDate >= today && bDate <= eightDaysLater
    }).sort((a, b) => {
      const dateA = parseBirthdayDate(a.date)
      const dateB = parseBirthdayDate(b.date)
      if (!dateA || !dateB) return 0
      dateA.setFullYear(today.getFullYear())
      dateB.setFullYear(today.getFullYear())
      return dateA.getTime() - dateB.getTime()
    })

    setUpcomingBirthdays(upcoming)
  }, [birthdays])

  return (
    <div className="flex flex-col gap-6">
      {/* Two columns: Announcements + Birthdays */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Left Column: Announcements */}
        <div className="flex flex-col gap-6">
          {/* Important Announcements */}
          <Card className="border-amber-500/30 bg-card">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-amber-500" />
                <CardTitle className="text-foreground">Важная информация</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-lg text-foreground whitespace-pre-line">
                {announcement?.active ? announcement.message : "Нет важных объявлений"}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Birthdays */}
        <Card className="border-pink-500/30 bg-card h-full">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Cake className="h-5 w-5 text-pink-500" />
              <CardTitle className="text-foreground">Дни рождения</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {upcomingBirthdays.length > 0 ? (
              <div className="space-y-4">
                {upcomingBirthdays.map((person, index) => (
                  <div key={index} className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-foreground">{person.name}</p>
                      <p className="text-sm text-muted-foreground">{person.company}</p>
                      <p className="text-sm text-muted-foreground">{person.position}</p>
                    </div>
                    <Badge variant="secondary" className="shrink-0 bg-pink-200 text-pink-700 dark:bg-pink-900/50 dark:text-pink-300">
                      {formatBirthdayDisplay(person.date)}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground">В ближайшие 8 дней именинников нет</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
