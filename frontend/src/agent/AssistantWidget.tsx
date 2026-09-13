import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import Avatar3D from './Avatar3D'
import { useAssistant } from './useAssistant'
import { useSpeech } from './useSpeech'
import type { AgentContext } from './types'
import './agent.css'

type Props = {
  step: number | null
  qIndex?: number | null
  context: AgentContext
  enabled?: boolean
  onHighlight?: (target: string) => void
}

export default function AssistantWidget({
  step,
  qIndex = null,
  context,
  enabled = true,
  onHighlight,
}: Props) {
  const [open, setOpen] = useState(
    () => typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('agent') === 'open',
  )
  const [input, setInput] = useState('')
  const [unread, setUnread] = useState(0)
  const [highlight, setHighlight] = useState<string | null>(null)
  const [caption, setCaption] = useState<string | null>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const { speak, stop, speaking, level, levelRef, muted, setMuted, needsGesture } = useSpeech()

  const { messages, busy, send, reset } = useAssistant({
    step,
    qIndex,
    context,
    enabled,
    onSpeak: (text, tone) => {
      setCaption(text)
      void speak(text, tone)
    },
    onReply: (reply) => {
      setHighlight(reply.highlight ?? null)
      if (reply.highlight) onHighlight?.(reply.highlight)
      if (!open) setUnread((n) => n + 1)
    },
  })

  useEffect(() => {
    if (needsGesture || speaking || !caption) return
    const timer = window.setTimeout(() => setCaption(null), 2500)
    return () => window.clearTimeout(timer)
  }, [speaking, needsGesture, caption])

  const suggestions = useMemo(() => {
    const last = [...messages].reverse().find((m) => m.role === 'assistant' && m.suggestions?.length)
    return last?.suggestions ?? []
  }, [messages])

  useEffect(() => {
    if (open) {
      setUnread(0)
      listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
    }
  }, [messages, open])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const text = input
    setInput('')
    await send(text)
  }

  const latest = [...messages].reverse().find((m) => m.role === 'assistant')

  function toggleOpen() {
    setOpen((was) => {
      if (was) {
        stop()
        return false
      }
      return true
    })
  }

  return (
    <>
      {!open && latest && unread > 0 && (
        <button type="button" className="ag-nudge" onClick={toggleOpen}>
          <span className="ag-nudge-name">Karim</span>
          <span className="ag-nudge-text">{latest.text}</span>
        </button>
      )}

      {open && (
        <section className="ag-panel" aria-label="Assistant Tasrih">
          <header className="ag-head">
            <div className="ag-head-left">
              <span className={`ag-dot ${speaking ? 'on' : ''}`} />
              <div>
                <strong>Karim</strong>
                <small>{speaking ? 'parle…' : busy ? 'réfléchit…' : 'assistant Tasrih'}</small>
              </div>
            </div>
            <div className="ag-head-right">
              <button
                type="button"
                className="ag-icon"
                title={muted ? 'Réactiver la voix' : 'Couper la voix'}
                onClick={() => {
                  if (!muted) stop()
                  setMuted(!muted)
                }}
              >
                {muted ? '🔇' : '🔊'}
              </button>
              <button
                type="button"
                className="ag-icon"
                title="Effacer la conversation"
                onClick={reset}
              >
                ↺
              </button>
              <button type="button" className="ag-icon" title="Fermer" onClick={toggleOpen}>
                ✕
              </button>
            </div>
          </header>

          <div className="ag-stage" data-highlight={highlight ?? undefined}>
            <span className="ag-stage-glow" />
            <Avatar3D levelRef={levelRef} speaking={speaking} variant="bust" />
            {caption && <div className="ag-subtitle">{caption}</div>}
          </div>

          <div className="ag-list" ref={listRef}>
            {messages.map((m) => (
              <div key={m.id} className={`ag-msg ${m.role}`}>
                {m.text}
              </div>
            ))}
            {busy && <div className="ag-typing">Karim écrit…</div>}
          </div>

          {suggestions.length > 0 && (
            <div className="ag-chips">
              {suggestions.map((s) => (
                <button key={s} type="button" className="ag-chip" onClick={() => void send(s)}>
                  {s}
                </button>
              ))}
            </div>
          )}

          <form className="ag-input" onSubmit={(e) => void onSubmit(e)}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Posez votre question…"
              aria-label="Votre message"
            />
            <button type="submit" className="ag-send" disabled={busy || !input.trim()}>
              ➤
            </button>
          </form>
        </section>
      )}

      {!open && caption && (
        <div className="ag-caption-bubble">{caption}</div>
      )}

      {needsGesture && !muted && (
        <span className="ag-voice-hint" role="status">
          🔊 Activez la voix
        </span>
      )}

      <button
        type="button"
        className={`ag-launcher ${speaking ? 'talking' : ''}`}
        onClick={toggleOpen}
        aria-label={open ? "Fermer l'assistant" : "Ouvrir l'assistant"}
      >
        <span className="ag-launcher-ring" style={{ transform: `scale(${1 + level * 0.25})` }} />
        {open ? (
          <span className="ag-launcher-face">K</span>
        ) : (
          <span className="ag-launcher-avatar">
            <Avatar3D levelRef={levelRef} speaking={speaking} variant="head" />
          </span>
        )}
        {unread > 0 && !open && <span className="ag-badge">{unread}</span>}
      </button>
    </>
  )
}
