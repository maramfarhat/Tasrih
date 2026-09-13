import type { AgentContext, AgentReply, ChatMessage } from './types'

const API = import.meta.env.VITE_API_URL || '/api'

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await res.text())
  return (await res.json()) as T
}

export function getGuidance(step: number | null, context: AgentContext): Promise<AgentReply> {
  return post<AgentReply>('/agent/guidance', { step, context: { ...context, step } })
}

export function askAgent(
  messages: Pick<ChatMessage, 'role' | 'text'>[],
  context: AgentContext,
): Promise<AgentReply> {
  return post<AgentReply>('/agent/chat', {
    messages: messages.map((m) => ({ role: m.role, content: m.text })),
    context,
  })
}
