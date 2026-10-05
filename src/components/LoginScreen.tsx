import { useState, type FormEvent } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface Props {
  onLogin: (username: string, password: string) => boolean
  onRegister: (username: string, password: string) => boolean
}

export function LoginScreen({ onLogin, onRegister }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const ok = mode === "login" ? onLogin(username.trim(), password) : onRegister(username.trim(), password)
    if (!ok) setPassword("")
  }

  return (
    <div className="mx-auto max-w-md p-4 pt-16">
      <Card>
        <CardHeader>
          <CardTitle>{mode === "login" ? "Anmelden" : "Registrieren"}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Benutzername</Label>
              <Input
                id="username"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Passwort</Label>
              <Input
                id="password"
                type="password"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                minLength={mode === "register" ? 6 : undefined}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full">
              {mode === "login" ? "Anmelden" : "Konto erstellen"}
            </Button>
          </form>
          <button
            type="button"
            className="mt-4 w-full text-center text-sm text-slate-500 hover:underline"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "Noch kein Konto? Jetzt registrieren" : "Bereits registriert? Anmelden"}
          </button>
        </CardContent>
      </Card>
    </div>
  )
}
