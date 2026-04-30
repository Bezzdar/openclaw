import { Sidebar } from "@/components/sidebar"
import { Header } from "@/components/header"
import { DashboardWidgets } from "@/components/dashboard-widgets"

export default function HomePage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <div className="mx-auto max-w-4xl">
            <DashboardWidgets />
          </div>
        </main>
      </div>
    </div>
  )
}
