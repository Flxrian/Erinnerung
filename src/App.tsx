import { useEffect } from "react"
import { toast, ToastContainer } from "react-toastify"
import "react-toastify/dist/ReactToastify.css"
import { LogOutIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { LoginScreen } from "@/components/LoginScreen"
import { ActivitiesTab } from "@/components/ActivitiesTab"
import { TicketsTab } from "@/components/TicketsTab"
import { AdminTab } from "@/components/AdminTab"
import { newId, usePersistentState } from "@/lib/storage"
import { ACTIVITY_LOG_INTERVAL_MS, ACTIVITY_LOG_LIMIT, defaultUsers, deviceActivities } from "@/lib/data"
import type { Activity, LogEntry, Ticket, TicketStatus, User } from "@/lib/types"

export default function App() {
  const [users, setUsers] = usePersistentState<User[]>("users", defaultUsers)
  const [currentUserId, setCurrentUserId] = usePersistentState<string | null>("session", null)
  const [activities, setActivities] = usePersistentState<Activity[]>("activities", [])
  const [activityLog, setActivityLog] = usePersistentState<LogEntry[]>("activityLog", [])
  const [tickets, setTickets] = usePersistentState<Ticket[]>("tickets", [])
  const [activeTab, setActiveTab] = usePersistentState("activeTab", "activities")

  // Aus der Benutzerliste abgeleitet, damit Rechteänderungen sofort greifen.
  const currentUser = users.find((u) => u.id === currentUserId) ?? null

  useEffect(() => {
    if (!currentUser) return
    const userId = currentUser.id
    const timer = setInterval(() => {
      const activity = deviceActivities[Math.floor(Math.random() * deviceActivities.length)]
      const entry: LogEntry = { id: newId(), userId, timestamp: new Date().toLocaleString("de-DE"), activity, shared: false }
      setActivityLog((prev) => {
        const own = prev.filter((l) => l.userId === userId)
        const others = prev.filter((l) => l.userId !== userId)
        return [entry, ...own].slice(0, ACTIVITY_LOG_LIMIT).concat(others)
      })
    }, ACTIVITY_LOG_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [currentUser?.id, setActivityLog])

  const isUsernameTaken = (username: string) =>
    users.some((u) => u.username.toLowerCase() === username.toLowerCase())

  const handleLogin = (username: string, password: string) => {
    const user = users.find((u) => u.username === username && u.password === password)
    if (!user) {
      toast.error("Ungültige Anmeldedaten!")
      return false
    }
    setCurrentUserId(user.id)
    toast.success("Erfolgreich angemeldet!")
    return true
  }

  const addUser = (username: string, password: string, isAdmin: boolean) => {
    if (!username || password.length < 6) {
      toast.error("Benutzername und ein Passwort mit mindestens 6 Zeichen sind erforderlich.")
      return null
    }
    if (isUsernameTaken(username)) {
      toast.error("Dieser Benutzername ist bereits vergeben.")
      return null
    }
    const user: User = { id: newId(), username, password, isAdmin }
    setUsers((prev) => [...prev, user])
    return user
  }

  const handleRegister = (username: string, password: string) => {
    const user = addUser(username, password, false)
    if (!user) return false
    setCurrentUserId(user.id)
    toast.success("Konto erstellt und angemeldet!")
    return true
  }

  const handleLogout = () => {
    setCurrentUserId(null)
    toast.info("Erfolgreich abgemeldet!")
  }

  const toaster = <ToastContainer position="top-right" autoClose={4000} />

  if (!currentUser) {
    return (
      <>
        {toaster}
        <LoginScreen onLogin={handleLogin} onRegister={handleRegister} />
      </>
    )
  }

  const tab = !currentUser.isAdmin && activeTab === "admin" ? "activities" : activeTab

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-4">
      {toaster}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">Willkommen, {currentUser.username}!</h1>
        <Button onClick={handleLogout}>
          <LogOutIcon className="mr-2 h-4 w-4" />
          Abmelden
        </Button>
      </div>
      <Tabs value={tab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="activities">Aktivitäten</TabsTrigger>
          <TabsTrigger value="tickets">Tickets</TabsTrigger>
          {currentUser.isAdmin && <TabsTrigger value="admin">Admin</TabsTrigger>}
        </TabsList>
        <TabsContent value="activities">
          <ActivitiesTab
            currentUser={currentUser}
            users={users}
            activities={activities}
            activityLog={activityLog}
            onAddActivity={(date, description) =>
              setActivities((prev) => [...prev, { id: newId(), userId: currentUser.id, date, description }])
            }
            onDeleteActivity={(id) => setActivities((prev) => prev.filter((a) => a.id !== id))}
            onToggleShare={(id) =>
              setActivityLog((prev) => prev.map((l) => (l.id === id ? { ...l, shared: !l.shared } : l)))
            }
            onClearLog={() => setActivityLog((prev) => prev.filter((l) => l.userId !== currentUser.id))}
          />
        </TabsContent>
        <TabsContent value="tickets">
          <TicketsTab
            currentUser={currentUser}
            tickets={tickets}
            onCreateTicket={(title, description) =>
              setTickets((prev) => [
                ...prev,
                {
                  id: prev.reduce((max, t) => Math.max(max, t.id), 0) + 1,
                  title,
                  description,
                  status: "Offen",
                  createdBy: currentUser.username,
                  createdAt: new Date().toLocaleString("de-DE"),
                },
              ])
            }
            onUpdateStatus={(id: number, status: TicketStatus) =>
              setTickets((prev) => prev.map((t) => (t.id === id ? { ...t, status } : t)))
            }
          />
        </TabsContent>
        {currentUser.isAdmin && (
          <TabsContent value="admin">
            <AdminTab
              currentUser={currentUser}
              users={users}
              onSetAdmin={(id, isAdmin) => setUsers((prev) => prev.map((u) => (u.id === id ? { ...u, isAdmin } : u)))}
              onAddUser={(username, password, isAdmin) => {
                const user = addUser(username, password, isAdmin)
                if (user) toast.success(`Benutzer ${user.username} angelegt!`)
                return user !== null
              }}
              onDeleteUser={(id) => {
                setUsers((prev) => prev.filter((u) => u.id !== id))
                setActivities((prev) => prev.filter((a) => a.userId !== id))
                setActivityLog((prev) => prev.filter((l) => l.userId !== id))
              }}
            />
          </TabsContent>
        )}
      </Tabs>
    </div>
  )
}
