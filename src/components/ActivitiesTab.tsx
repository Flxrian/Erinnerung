import { useState, type FormEvent } from "react"
import { CalendarIcon, LockIcon, PlusCircleIcon, ShareIcon, Trash2Icon } from "lucide-react"
import { toast } from "react-toastify"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Activity, LogEntry, User } from "@/lib/types"

// "2026-10-05" -> "05.10.2026" (ohne Date-Parsing, das sonst je nach Zeitzone den Tag verschiebt)
const formatDate = (iso: string) => iso.split("-").reverse().join(".")

interface Props {
  currentUser: User
  users: User[]
  activities: Activity[]
  activityLog: LogEntry[]
  onAddActivity: (date: string, description: string) => void
  onDeleteActivity: (id: string) => void
  onToggleShare: (id: string) => void
  onClearLog: () => void
}

export function ActivitiesTab({
  currentUser,
  users,
  activities,
  activityLog,
  onAddActivity,
  onDeleteActivity,
  onToggleShare,
  onClearLog,
}: Props) {
  const [shareMode, setShareMode] = useState(false)
  const [date, setDate] = useState("")
  const [description, setDescription] = useState("")

  const myActivities = activities
    .filter((a) => a.userId === currentUser.id)
    .sort((a, b) => b.date.localeCompare(a.date))
  const myLog = activityLog.filter((l) => l.userId === currentUser.id)
  // Geteilte Einträge aller Benutzer – so sehen andere, was geteilt wurde.
  const sharedLog = activityLog.filter((l) => l.shared)
  const usernameOf = (id: string) => users.find((u) => u.id === id)?.username ?? "Unbekannt"

  const toggleShareMode = () => {
    setShareMode(!shareMode)
    toast.info(
      shareMode
        ? "Aktivitäten-Sharing-Modus deaktiviert."
        : "Aktivitäten-Sharing-Modus aktiviert. Wählen Sie Aktivitäten zum Teilen aus.",
    )
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!date || !description.trim()) return
    onAddActivity(date, description.trim())
    setDate("")
    setDescription("")
    toast.success("Aktivität hinzugefügt!")
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center justify-between gap-2">
            <span>Aktivitäts-Tracker</span>
            <Button onClick={toggleShareMode} variant="outline">
              {shareMode ? <LockIcon className="mr-2 h-4 w-4" /> : <ShareIcon className="mr-2 h-4 w-4" />}
              {shareMode ? "Sharing-Modus aus" : "Sharing-Modus an"}
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex flex-col space-y-2">
              <Label htmlFor="activity-date">Datum</Label>
              <Input id="activity-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
            </div>
            <div className="flex flex-col space-y-2">
              <Label htmlFor="activity-description">Beschreibung</Label>
              <Input
                id="activity-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                required
              />
            </div>
            <Button type="submit">
              <PlusCircleIcon className="mr-2 h-4 w-4" />
              Aktivität hinzufügen
            </Button>
          </form>
          <div className="mt-6">
            <h3 className="mb-2 font-semibold">Manuell hinzugefügte Aktivitäten:</h3>
            {myActivities.length === 0 ? (
              <p className="text-sm text-slate-500">Noch keine Aktivitäten erfasst.</p>
            ) : (
              <ul className="space-y-2">
                {myActivities.map((activity) => (
                  <li key={activity.id} className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-2">
                      <CalendarIcon className="h-4 w-4 shrink-0" />
                      <span>
                        {formatDate(activity.date)}: {activity.description}
                      </span>
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Aktivität löschen"
                      onClick={() => onDeleteActivity(activity.id)}
                    >
                      <Trash2Icon className="h-4 w-4" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center justify-between gap-2">
            <span>Automatisches Aktivitätsprotokoll</span>
            {myLog.length > 0 && (
              <Button variant="outline" size="sm" onClick={onClearLog}>
                Protokoll leeren
              </Button>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {myLog.length === 0 ? (
            <p className="text-sm text-slate-500">
              Noch keine Einträge – alle 30 Sekunden wird eine Geräteaktivität protokolliert.
            </p>
          ) : (
            <ul className="max-h-60 space-y-2 overflow-y-auto">
              {myLog.map((log) => (
                <li key={log.id} className="flex items-center justify-between gap-2 text-sm">
                  <span>
                    <span className="font-semibold">{log.timestamp}:</span>
                    <span className="ml-2">{log.activity}</span>
                  </span>
                  {shareMode ? (
                    <Checkbox
                      checked={log.shared}
                      onCheckedChange={() => onToggleShare(log.id)}
                      aria-label="Aktivität teilen"
                    />
                  ) : (
                    log.shared && <ShareIcon className="h-4 w-4 text-slate-400" aria-label="Geteilt" />
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Geteilte Aktivitäten</CardTitle>
        </CardHeader>
        <CardContent>
          {sharedLog.length === 0 ? (
            <p className="text-sm text-slate-500">Es wurden noch keine Aktivitäten geteilt.</p>
          ) : (
            <ul className="max-h-60 space-y-2 overflow-y-auto">
              {sharedLog.map((log) => (
                <li key={log.id} className="flex items-center gap-2 text-sm">
                  <ShareIcon className="h-4 w-4 shrink-0" />
                  <span className="font-semibold">{log.timestamp}:</span>
                  <span>{log.activity}</span>
                  <span className="text-slate-500">({usernameOf(log.userId)})</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
