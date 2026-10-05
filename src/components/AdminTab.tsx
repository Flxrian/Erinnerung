import { useState, type FormEvent } from "react"
import { Trash2Icon, UserIcon, UserPlusIcon } from "lucide-react"
import { toast } from "react-toastify"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { User } from "@/lib/types"

interface Props {
  currentUser: User
  users: User[]
  onSetAdmin: (id: string, isAdmin: boolean) => void
  onAddUser: (username: string, password: string, isAdmin: boolean) => boolean
  onDeleteUser: (id: string) => void
}

export function AdminTab({ currentUser, users, onSetAdmin, onAddUser, onDeleteUser }: Props) {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [isAdmin, setIsAdmin] = useState(false)
  const adminCount = users.filter((u) => u.isAdmin).length

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (onAddUser(username.trim(), password, isAdmin)) {
      setUsername("")
      setPassword("")
      setIsAdmin(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Admin-Bereich</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <h3 className="mb-2 font-semibold">Benutzer verwalten:</h3>
          <ul className="space-y-2">
            {users.map((user) => {
              const isSelf = user.id === currentUser.id
              const isLastAdmin = user.isAdmin && adminCount === 1
              return (
                <li key={user.id} className="flex flex-wrap items-center justify-between gap-2">
                  <span className="flex items-center">
                    <UserIcon className="mr-2 h-4 w-4" />
                    {user.username} {user.isAdmin && "(Admin)"} {isSelf && "– Sie"}
                  </span>
                  <span className="flex gap-2">
                    {user.isAdmin ? (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={isLastAdmin || isSelf}
                        onClick={() => {
                          onSetAdmin(user.id, false)
                          toast.info(`${user.username} ist kein Admin mehr.`)
                        }}
                      >
                        Admin-Rechte entziehen
                      </Button>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          onSetAdmin(user.id, true)
                          toast.success(`${user.username} ist jetzt ein Admin!`)
                        }}
                      >
                        Zum Admin machen
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`${user.username} löschen`}
                      disabled={isSelf || isLastAdmin}
                      onClick={() => {
                        if (confirm(`Benutzer „${user.username}“ wirklich löschen?`)) {
                          onDeleteUser(user.id)
                          toast.info(`${user.username} wurde gelöscht.`)
                        }
                      }}
                    >
                      <Trash2Icon className="h-4 w-4" />
                    </Button>
                  </span>
                </li>
              )
            })}
          </ul>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 border-t border-slate-200 pt-4">
          <h3 className="font-semibold">Neuen Benutzer anlegen:</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="new-username">Benutzername</Label>
              <Input id="new-username" value={username} onChange={(e) => setUsername(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new-password">Passwort</Label>
              <Input
                id="new-password"
                type="password"
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox id="new-is-admin" checked={isAdmin} onCheckedChange={(v) => setIsAdmin(v === true)} />
            <Label htmlFor="new-is-admin">Admin-Rechte</Label>
          </div>
          <Button type="submit">
            <UserPlusIcon className="mr-2 h-4 w-4" />
            Benutzer anlegen
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
