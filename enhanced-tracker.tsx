"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { CalendarIcon, PlusCircleIcon, ShareIcon, LockIcon, UserIcon, TicketIcon, AlertTriangleIcon } from 'lucide-react'
import { toast, ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'

// Simulated database
let users = [
  { id: 1, username: 'admin', password: 'admin123', isAdmin: true },
  { id: 2, username: 'user1', password: 'user123', isAdmin: false },
]

let tickets = []

const deviceActivities = [
  "Geöffneter Webbrowser",
  "E-Mail überprüft",
  "Dokument-Editor geöffnet",
  "Videoanruf gestartet",
  "Musik-Player geöffnet",
  "Dateimanager zugegriffen",
  "Kalender-App geöffnet",
  "Coding IDE gestartet",
  "Messaging-App geöffnet",
  "Systemeinstellungen aufgerufen"
]

export default function Component() {
  const [activities, setActivities] = useState([])
  const [newActivity, setNewActivity] = useState({ date: "", description: "" })
  const [activityLog, setActivityLog] = useState([])
  const [sharedActivities, setSharedActivities] = useState([])
  const [shareMode, setShareMode] = useState(false)
  const [currentUser, setCurrentUser] = useState(null)
  const [loginUsername, setLoginUsername] = useState("")
  const [loginPassword, setLoginPassword] = useState("")
  const [newTicket, setNewTicket] = useState({ title: "", description: "" })
  const [showTicketDialog, setShowTicketDialog] = useState(false)

  useEffect(() => {
    const logActivity = () => {
      if (currentUser) {
        const randomActivity = deviceActivities[Math.floor(Math.random() * deviceActivities.length)]
        const newLogEntry = {
          timestamp: new Date().toLocaleString(),
          activity: randomActivity,
          shared: false
        }
        setActivityLog(prevLog => [newLogEntry, ...prevLog].slice(0, 50))
      }
    }

    const activityLogger = setInterval(logActivity, 30000)

    return () => clearInterval(activityLogger)
  }, [currentUser])

  const addActivity = (e) => {
    e.preventDefault()
    if (newActivity.date && newActivity.description) {
      setActivities([...activities, newActivity])
      setNewActivity({ date: "", description: "" })
    }
  }

  const toggleShareMode = () => {
    setShareMode(!shareMode)
    if (!shareMode) {
      toast.info("Aktivitäten-Sharing-Modus aktiviert. Wählen Sie Aktivitäten zum Teilen aus.", {
        position: "top-right",
        autoClose: 5000,
      })
    } else {
      toast.info("Aktivitäten-Sharing-Modus deaktiviert.", {
        position: "top-right",
        autoClose: 5000,
      })
    }
  }

  const toggleShareActivity = (index) => {
    const updatedLog = [...activityLog]
    updatedLog[index].shared = !updatedLog[index].shared
    setActivityLog(updatedLog)

    if (updatedLog[index].shared) {
      setSharedActivities([...sharedActivities, updatedLog[index]])
    } else {
      setSharedActivities(sharedActivities.filter(activity => activity !== updatedLog[index]))
    }
  }

  const handleLogin = (e) => {
    e.preventDefault()
    const user = users.find(u => u.username === loginUsername && u.password === loginPassword)
    if (user) {
      setCurrentUser(user)
      toast.success("Erfolgreich angemeldet!")
    } else {
      toast.error("Ungültige Anmeldedaten!")
    }
  }

  const handleLogout = () => {
    setCurrentUser(null)
    setLoginUsername("")
    setLoginPassword("")
    toast.info("Erfolgreich abgemeldet!")
  }

  const handleSubmitTicket = (e) => {
    e.preventDefault()
    if (newTicket.title && newTicket.description) {
      const ticket = {
        id: tickets.length + 1,
        ...newTicket,
        status: 'Offen',
        createdBy: currentUser.username,
        createdAt: new Date().toLocaleString()
      }
      tickets.push(ticket)
      setNewTicket({ title: "", description: "" })
      setShowTicketDialog(false)
      toast.success("Ticket erfolgreich erstellt!")
    }
  }

  const updateTicketStatus = (ticketId, newStatus) => {
    tickets = tickets.map(ticket => 
      ticket.id === ticketId ? { ...ticket, status: newStatus } : ticket
    )
    toast.success("Ticket-Status aktualisiert!")
  }

  if (!currentUser) {
    return (
      <div className="container mx-auto p-4 max-w-md">
        <Card>
          <CardHeader>
            <CardTitle>Anmelden</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username">Benutzername</Label>
                <Input
                  id="username"
                  type="text"
                  value={loginUsername}
                  onChange={(e) => setLoginUsername(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Passwort</Label>
                <Input
                  id="password"
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  required
                />
              </div>
              <Button type="submit" className="w-full">Anmelden</Button>
            </form>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-4 space-y-6">
      <ToastContainer />
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Willkommen, {currentUser.username}!</h1>
        <Button onClick={handleLogout}>Abmelden</Button>
      </div>
      <Tabs defaultValue="activities">
        <TabsList>
          <TabsTrigger value="activities">Aktivitäten</TabsTrigger>
          <TabsTrigger value="tickets">Tickets</TabsTrigger>
          {currentUser.isAdmin && <TabsTrigger value="admin">Admin</TabsTrigger>}
        </TabsList>
        <TabsContent value="activities">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Aktivitäts-Tracker</span>
                <Button onClick={toggleShareMode} variant="outline">
                  {shareMode ? <LockIcon className="mr-2 h-4 w-4" /> : <ShareIcon className="mr-2 h-4 w-4" />}
                  {shareMode ? "Sharing-Modus aus" : "Sharing-Modus an"}
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={addActivity} className="space-y-4">
                <div className="flex flex-col space-y-2">
                  <Label htmlFor="activity-date">Datum</Label>
                  <Input
                    id="activity-date"
                    type="date"
                    value={newActivity.date}
                    onChange={(e) => setNewActivity({ ...newActivity, date: e.target.value })}
                    required
                  />
                </div>
                <div className="flex flex-col space-y-2">
                  <Label htmlFor="activity-description">Beschreibung</Label>
                  <Input
                    id="activity-description"
                    type="text"
                    value={newActivity.description}
                    onChange={(e) => setNewActivity({ ...newActivity, description: e.target.value })}
                    required
                  />
                </div>
                <Button type="submit">
                  <PlusCircleIcon className="mr-2 h-4 w-4" />
                  Aktivität hinzufügen
                </Button>
              </form>
              <div className="mt-4">
                <h3 className="font-semibold mb-2">Manuell hinzugefügte Aktivitäten:</h3>
                <ul className="space-y-2">
                  {activities.map((activity, index) => (
                    <li key={index} className="flex items-center space-x-2">
                      <CalendarIcon className="h-4 w-4" />
                      <span>{activity.date}: {activity.description}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </CardContent>
          </Card>

          <Card className="mt-4">
            <CardHeader>
              <CardTitle>Automatisches Aktivitätsprotokoll</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mt-4 max-h-60 overflow-y-auto">
                <ul className="space-y-2">
                  {activityLog.map((log, index) => (
                    <li key={index} className="flex items-center justify-between text-sm">
                      <span>
                        <span className="font-semibold">{log.timestamp}:</span>
                        <span className="ml-2">{log.activity}</span>
                      </span>
                      {shareMode && (
                        <Checkbox
                          checked={log.shared}
                          onCheckedChange={() => toggleShareActivity(index)}
                        />
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            </CardContent>
          </Card>

          {shareMode && (
            <Card className="mt-4">
              <CardHeader>
                <CardTitle>Geteilte Aktivitäten</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="mt-4 max-h-60 overflow-y-auto">
                  <ul className="space-y-2">
                    {sharedActivities.map((activity, index) => (
                      <li key={index} className="flex items-center space-x-2 text-sm">
                        <ShareIcon className="h-4 w-4" />
                        <span className="font-semibold">{activity.timestamp}:</span>
                        <span>{activity.activity}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
        <TabsContent value="tickets">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Tickets</span>
                <Dialog open={showTicketDialog} onOpenChange={setShowTicketDialog}>
                  <DialogTrigger asChild>
                    <Button>
                      <PlusCircleIcon className="mr-2 h-4 w-4" />
                      Neues Ticket
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Neues Ticket erstellen</DialogTitle>
                      <DialogDescription>
                        Beschreiben Sie das Problem oder den Fehler, den Sie gefunden haben.
                      </DialogDescription>
                    </DialogHeader>
                    <form onSubmit={handleSubmitTicket} className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="ticket-title">Titel</Label>
                        <Input
                          id="ticket-title"
                          value={newTicket.title}
                          onChange={(e) => setNewTicket({ ...newTicket, title: e.target.value })}
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="ticket-description">Beschreibung</Label>
                        <Input
                          id="ticket-description"
                          value={newTicket.description}
                          onChange={(e) => setNewTicket({ ...newTicket, description: e.target.value })}
                          required
                        />
                      </div>
                      <Button type="submit">Ticket einreichen</Button>
                    </form>
                  </DialogContent>
                </Dialog>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {tickets.map((ticket) => (
                  <Card key={ticket.id}>
                    <CardHeader>
                      <CardTitle className="flex items-center justify-between">
                        <span>{ticket.title}</span>
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          ticket.status === 'Offen' ? 'bg-yellow-200 text-yellow-800' :
                          ticket.status === 'In Bearbeitung' ? 'bg-blue-200 text-blue-800' :
                          'bg-green-200 text-green-800'
                        }`}>
                          {ticket.status}
                        </span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p>{ticket.description}</p>
                      <div className="mt-2 text-sm text-gray-500">
                        Erstellt von {ticket.createdBy} am {ticket.createdAt}
                      </div>
                      {currentUser.isAdmin && (
                        <div className="mt-4 space-x-2">
                          <Button onClick={() => updateTicketStatus(ticket.id, 'In Bearbeitung')} variant="outline" size="sm">
                            In Bearbeitung
                          </Button>
                          <Button onClick={() => updateTicketStatus(ticket.id, 'Geschlossen')} variant="outline" size="sm">
                            Schließen
                          </Button>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        {currentUser.isAdmin && (
          <TabsContent value="admin">
            <Card>
              <CardHeader>
                <CardTitle>Admin-Bereich</CardTitle>
              </CardHeader>
              <CardContent>
                <h3 className="font-semibold mb-2">Benutzer verwalten:</h3>
                <ul className="space-y-2">
                  {users.map((user) => (
                    <li key={user.id} className="flex items-center justify-between">
                      <span>
                        <UserIcon className="inline-block mr-2 h-4 w-4" />
                        {user.username} {user.isAdmin && "(Admin)"}
                      </span>
                      {!user.isAdmin && (
                        <Button variant="outline" size="sm" onClick={() => {
                          users = users.map(u => u.id === user.id ? { ...u, isAdmin: true } : u)
                          toast.success(`${user.username} ist jetzt ein Admin!`)
                        }}>
                          Zum Admin machen
                        </Button>
                      )}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </TabsContent>
        )}
      </Tabs>
    </div>
  )
}