import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import Avatar3D from './Avatar3D'
import { useAssistant } from './useAssistant'
import { useSpeech } from './useSpeech'
import { useI18n } from '../i18n'
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
  const { t, tr, lang } = useI18n()
  const [input, setInput] = useState('')
  const [highlight, setHighlight] = useState<string | null>(null)
  const [caption, setCaption] = useState<string | null>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const { speak, stop, speaking, level, levelRef, muted, setMuted, needsGesture } = useSpeech(
    '/api/agent/tts',
    lang,
  )

  const { messages, busy, send, reset } = useAssistant({
    step,
    qIndex,
    context,
    enabled,
    lang,
    onSpeak: (text, tone) => {
      // Karim reprend la parole à chaque étape, mais speak() coupe d'abord
      // la voix précédente : jamais deux voix en même temps.
      setCaption(text)
      void speak(lang === 'ar' ? tr(text) : text, tone)
    },
    onReply: (reply) => {
      setHighlight(reply.highlight ?? null)
      if (reply.highlight) onHighlight?.(reply.highlight)
    },
  })

  // Changement de page / d'étape : on coupe immédiatement la voix en cours.
  useEffect(() => {
    stop()
  }, [step, qIndex, stop])

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
      listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
    }
  }, [messages, open])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const text = input
    setInput('')
    await send(text)
  }

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
      {open && (
        <section className="ag-panel" aria-label="Assistant Tasrih">
          <header className="ag-head">
            <div className="ag-head-left">
              <span className={`ag-dot ${speaking ? 'on' : ''}`} />
              <div>
                <strong>Karim</strong>
                <small>
                  {speaking ? t('parle…') : busy ? t('réfléchit…') : t('assistant Tasrih')}
                </small>
              </div>
            </div>
            <div className="ag-head-right">
              <button
                type="button"
                className="ag-icon"
                title={muted ? t('Réactiver la voix') : t('Couper la voix')}
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
                title={t('Effacer la conversation')}
                onClick={reset}
              >
                ↺
              </button>
              <button
                type="button"
                className="ag-icon"
                title={t('Fermer')}
                onClick={toggleOpen}
              >
                ✕
              </button>
            </div>
          </header>

          <div className="ag-stage" data-highlight={highlight ?? undefined}>
            <span className="ag-stage-glow" />
            <Avatar3D levelRef={levelRef} speaking={speaking} variant="half" />
            {caption && <div className="ag-subtitle">{caption}</div>}
          </div>

          <div className="ag-list" ref={listRef}>
            {messages.map((m) => (
              <div key={m.id} className={`ag-msg ${m.role}`}>
                {m.text}
              </div>
            ))}
            {busy && <div className="ag-typing">{t('Karim écrit…')}</div>}
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
              placeholder={t('Posez votre question…')}
              aria-label={t('Posez votre question…')}
            />
            <button type="submit" className="ag-send" disabled={busy || !input.trim()}>
              ➤
            </button>
          </form>
        </section>
      )}

      {needsGesture && !muted && (
        <span className="ag-voice-hint" role="status">
          🔊 {t('Activez la voix')}
        </span>
      )}

      <button
        type="button"
        className={`ag-launcher ${speaking ? 'talking' : ''}`}
        onClick={toggleOpen}
        aria-label={open ? t("Fermer l'assistant") : t('Ouvrir l’assistant')}
      >
        <span className="ag-launcher-ring" style={{ transform: `scale(${1 + level * 0.25})` }} />
        {open ? (
          <span className="ag-launcher-face">K</span>
        ) : (
          <span className="ag-launcher-avatar">
            <Avatar3D levelRef={levelRef} speaking={speaking} variant="head" />
          </span>
        )}
      </button>
    </>
  )
}
