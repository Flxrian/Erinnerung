export interface User {
  id: string
  username: string
  password: string
  isAdmin: boolean
}

export interface Activity {
  id: string
  userId: string
  date: string
  description: string
}

export interface LogEntry {
  id: string
  userId: string
  timestamp: string
  activity: string
  shared: boolean
}

export type TicketStatus = "Offen" | "In Bearbeitung" | "Geschlossen"

export interface Ticket {
  id: number
  title: string
  description: string
  status: TicketStatus
  createdBy: string
  createdAt: string
}
