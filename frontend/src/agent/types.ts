export type ChatRole = 'user' | 'assistant'

export type ChatMessage = {
  id: string
  role: ChatRole
  text: string
  suggestions?: string[]
}

export type AgentContext = {
  step: number | null
  step_label?: string | null
  q_index?: number | null
  profile?: Record<string, unknown> | null
  cif?: Record<string, unknown> | null
  rne?: Record<string, unknown> | null
  onboarding?: Record<string, unknown> | null
  invoices?: Record<string, unknown>[] | null
  amounts?: Record<string, unknown> | null
  needs_user_review?: string[] | null
  confidence?: number | null
  logged_in?: boolean | null
}

export type AgentReply = {
  reply: string
  suggestions: string[]
  highlight?: string | null
  step?: number | null
  tone?: string
  source: string
}
