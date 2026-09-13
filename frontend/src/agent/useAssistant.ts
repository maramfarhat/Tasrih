import { useCallback, useEffect, useRef, useState } from 'react'
import { askAgent, getGuidance } from './api'
import type { AgentContext, AgentReply, ChatMessage } from './types'

let counter = 0
const uid = () => `m${Date.now().toString(36)}_${counter++}`

type Options = {
  step: number | null
  qIndex?: number | null
  context: AgentContext
  enabled?: boolean
  onSpeak?: (text: string, tone?: string) => void
  onReply?: (reply: AgentReply) => void
}

export function useAssistant({
  step,
  qIndex = null,
  context,
  enabled = true,
  onSpeak,
  onReply,
}: Options) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [busy, setBusy] = useState(false)

  const msgsRef = useRef<ChatMessage[]>([])
  const ctxRef = useRef(context)
  const cbRef = useRef({ onSpeak, onReply })
  const enabledRef = useRef(enabled)
  const keyRef = useRef<string | null>(null)

  useEffect(() => {
    ctxRef.current = context
  }, [context])
  useEffect(() => {
    cbRef.current = { onSpeak, onReply }
  }, [onSpeak, onReply])
  useEffect(() => {
    enabledRef.current = enabled
  }, [enabled])

  const push = useCallback((msg: ChatMessage) => {
    const next = [...msgsRef.current, msg]
    msgsRef.current = next
    setMessages(next)
  }, [])

  /** Message proactif quand on change d'écran. */
  useEffect(() => {
    if (!enabled) return
    // logged_in différencie l'accueil connecté de la page d'authentification (step 0)
    const key = `${step}:${qIndex}:${ctxRef.current.logged_in ? 'in' : 'out'}`
    if (keyRef.current === key) return
    keyRef.current = key
    setBusy(true)
    if (import.meta.env.DEV) console.debug('[assistant] guidance →', key)
    void getGuidance(step, { ...ctxRef.current, step, q_index: qIndex })
      .then((reply) => {
        if (import.meta.env.DEV) console.debug('[assistant] guidance ✓', reply.reply.slice(0, 30))
        push({ id: uid(), role: 'assistant', text: reply.reply, suggestions: reply.suggestions })
        cbRef.current.onReply?.(reply)
        cbRef.current.onSpeak?.(reply.reply, reply.tone)
      })
      .catch((e) => {
        if (import.meta.env.DEV) console.debug('[assistant] guidance ✗', String(e))
      })
      .finally(() => setBusy(false))
  }, [step, qIndex, enabled, push])

  const send = useCallback(
    async (text: string) => {
      const clean = text.trim()
      if (!clean) return
      push({ id: uid(), role: 'user', text: clean })
      setBusy(true)
      try {
        const reply = await askAgent(
          msgsRef.current.map((m) => ({ role: m.role, text: m.text })),
          { ...ctxRef.current, step },
        )
        push({ id: uid(), role: 'assistant', text: reply.reply, suggestions: reply.suggestions })
        cbRef.current.onReply?.(reply)
        cbRef.current.onSpeak?.(reply.reply, reply.tone)
      } catch {
        push({
          id: uid(),
          role: 'assistant',
          text: "Désolé, je n'arrive pas à répondre pour le moment. Réessayez dans un instant.",
        })
      } finally {
        setBusy(false)
      }
    },
    [push, step],
  )

  const reset = useCallback(() => {
    msgsRef.current = []
    setMessages([])
    keyRef.current = null
  }, [])

  return { messages, busy, send, reset }
}
