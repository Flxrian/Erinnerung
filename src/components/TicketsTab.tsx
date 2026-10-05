import { useState, type FormEvent } from "react"
import { PlusCircleIcon, TicketIcon } from "lucide-react"
import { toast } from "react-toastify"
import { Button } from "@/components/ui/button"
import { Input, Textarea } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import type { Ticket, TicketStatus, User } from "@/lib/types"

const statusStyles: Record<TicketStatus, string> = {
  Offen: "bg-yellow-200 text-yellow-800",
  "In Bearbeitung": "bg-blue-200 text-blue-800",
  Geschlossen: "bg-green-200 text-green-800",
}

interface Props {
  currentUser: User
  tickets: Ticket[]
  onCreateTicket: (title: string, description: string) => void
  onUpdateStatus: (id: number, status: TicketStatus) => void
}

export function TicketsTab({ currentUser, tickets, onCreateTicket, onUpdateStatus }: Props) {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")

  // Admins sehen alle Tickets, normale Benutzer nur ihre eigenen.
  const visibleTickets = (currentUser.isAdmin ? tickets : tickets.filter((t) => t.createdBy === currentUser.username))
    .slice()
    .sort((a, b) => b.id - a.id)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !description.trim()) return
    onCreateTicket(title.trim(), description.trim())
    setTitle("")
    setDescription("")
    setOpen(false)
    toast.success("Ticket erfolgreich erstellt!")
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center justify-between gap-2">
          <span>Tickets</span>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button>
                <PlusCircleIcon className="mr-2 h-4 w-4" />
                Neues Ticket
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Neues Ticket erstellen</DialogTitle>
                <DialogDescription>Beschreiben Sie das Problem oder den Fehler, den Sie gefunden haben.</DialogDescription>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="ticket-title">Titel</Label>
                  <Input id="ticket-title" value={title} onChange={(e) => setTitle(e.target.value)} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ticket-description">Beschreibung</Label>
                  <Textarea
                    id="ticket-description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
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
        {visibleTickets.length === 0 ? (
          <p className="flex items-center gap-2 text-sm text-slate-500">
            <TicketIcon className="h-4 w-4" /> Keine Tickets vorhanden.
          </p>
        ) : (
          <div className="space-y-4">
            {visibleTickets.map((ticket) => (
              <Card key={ticket.id}>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between gap-2 text-lg">
                    <span>
                      #{ticket.id} {ticket.title}
                    </span>
                    <span className={`rounded-full px-2 py-1 text-xs ${statusStyles[ticket.status]}`}>
                      {ticket.status}
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="whitespace-pre-wrap">{ticket.description}</p>
                  <div className="mt-2 text-sm text-slate-500">
                    Erstellt von {ticket.createdBy} am {ticket.createdAt}
                  </div>
                  {currentUser.isAdmin && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {(["Offen", "In Bearbeitung", "Geschlossen"] as const).map((status) => (
                        <Button
                          key={status}
                          variant="outline"
                          size="sm"
                          disabled={ticket.status === status}
                          onClick={() => {
                            onUpdateStatus(ticket.id, status)
                            toast.success("Ticket-Status aktualisiert!")
                          }}
                        >
                          {status === "Geschlossen" ? "Schließen" : status === "Offen" ? "Wieder öffnen" : status}
                        </Button>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
