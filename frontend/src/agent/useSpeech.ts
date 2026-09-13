import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Synthèse vocale de l'assistant.
 *
 * Préfère l'audio réel de Piper via `/agent/tts` (amplitude → bouche de l'avatar),
 * et retombe sur la voix du navigateur sinon.
 *
 * Contrainte navigateur : aucun son n'est autorisé avant une interaction de
 * l'utilisateur. On débloque donc l'audio au premier clic/touche, et on met de
 * côté le dernier message à dire pour le jouer dès le déblocage.
 */
export type SpeechStatus = 'idle' | 'loading' | 'speaking'

export function useSpeech(ttsUrl = '/api/agent/tts') {
  const [status, setStatus] = useState<SpeechStatus>('idle')
  const [muted, setMuted] = useState(false)
  const [level, setLevel] = useState(0)
  const [needsGesture, setNeedsGesture] = useState(true)

  const levelRef = useRef(0)
  const lastLevelPush = useRef(0)

  const audioCtxRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const sourceRef = useRef<AudioBufferSourceNode | null>(null)
  const rafRef = useRef<number | null>(null)
  const mutedRef = useRef(muted)
  const voiceRef = useRef<SpeechSynthesisVoice | null>(null)
  const activeRef = useRef(0)
  const unlockedRef = useRef(false)
  const pendingRef = useRef<{ text: string; tone?: string } | null>(null)
  const speakRef = useRef<(text: string, tone?: string) => void>(() => {})

  const pushLevel = useCallback((v: number) => {
    levelRef.current = v
    const now = performance.now()
    if (now - lastLevelPush.current > 55) {
      lastLevelPush.current = now
      setLevel(v)
    }
  }, [])

  useEffect(() => {
    mutedRef.current = muted
    if (muted) {
      try {
        window.speechSynthesis?.cancel()
      } catch {
        /* ignore */
      }
    }
  }, [muted])

  // choisir une voix française quand elle devient disponible
  useEffect(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return
    const pick = () => {
      const voices = window.speechSynthesis.getVoices()
      voiceRef.current =
        voices.find((v) => /^fr(-|_)/i.test(v.lang) && /google|natural|premium/i.test(v.name)) ||
        voices.find((v) => /^fr(-|_)/i.test(v.lang)) ||
        null
    }
    pick()
    window.speechSynthesis.addEventListener('voiceschanged', pick)
    return () => window.speechSynthesis.removeEventListener('voiceschanged', pick)
  }, [])

  const stopLevelLoop = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
  }, [])

  const stop = useCallback(() => {
    activeRef.current += 1
    stopLevelLoop()
    try {
      window.speechSynthesis?.cancel()
    } catch {
      /* ignore */
    }
    try {
      sourceRef.current?.stop()
    } catch {
      /* ignore */
    }
    sourceRef.current = null
    levelRef.current = 0
    setLevel(0)
    setStatus('idle')
  }, [stopLevelLoop])

  const runFakeLevel = useCallback(
    (token: number) => {
      const start = performance.now()
      const tick = () => {
        if (token !== activeRef.current) return
        const t = (performance.now() - start) / 1000
        const envelope = 0.45 + 0.4 * Math.abs(Math.sin(t * 9.5))
        const jitter = 0.75 + 0.25 * Math.abs(Math.sin(t * 31))
        pushLevel(Math.min(1, envelope * jitter))
        rafRef.current = requestAnimationFrame(tick)
      }
      rafRef.current = requestAnimationFrame(tick)
    },
    [pushLevel],
  )

  const runRealLevel = useCallback(
    (token: number) => {
      const tick = () => {
        if (token !== activeRef.current) return
        const analyser = analyserRef.current
        if (analyser) {
          const data = new Uint8Array(analyser.frequencyBinCount)
          analyser.getByteTimeDomainData(data)
          let sum = 0
          for (let i = 0; i < data.length; i += 1) {
            const v = (data[i] - 128) / 128
            sum += v * v
          }
          pushLevel(Math.min(1, Math.sqrt(sum / data.length) * 3.2))
        }
        rafRef.current = requestAnimationFrame(tick)
      }
      rafRef.current = requestAnimationFrame(tick)
    },
    [pushLevel],
  )

  const speakBrowser = useCallback(
    (text: string, token: number) => {
      const synth = window.speechSynthesis
      if (!synth) {
        setStatus('idle')
        return
      }
      synth.cancel()
      const utter = new SpeechSynthesisUtterance(text)
      utter.lang = 'fr-FR'
      utter.rate = 1
      utter.pitch = 1
      if (voiceRef.current) utter.voice = voiceRef.current
      utter.onstart = () => {
        if (token !== activeRef.current) return
        setStatus('speaking')
        runFakeLevel(token)
      }
      const finish = () => {
        if (token !== activeRef.current) return
        stopLevelLoop()
        levelRef.current = 0
        setLevel(0)
        setStatus('idle')
      }
      utter.onend = finish
      utter.onerror = finish
      synth.speak(utter)
    },
    [runFakeLevel, stopLevelLoop],
  )

  const speak = useCallback(
    async (text: string, tone?: string) => {
      const clean = (text || '').trim()
      if (!clean || mutedRef.current) return

      // pas encore d'interaction → on garde le message pour plus tard
      if (!unlockedRef.current) {
        if (import.meta.env.DEV) console.debug('[voice] queued (waiting gesture):', clean.slice(0, 40), tone ?? '')
        pendingRef.current = { text: clean, tone }
        setStatus('loading')
        return
      }

      activeRef.current += 1
      const token = activeRef.current
      stopLevelLoop()
      setStatus('loading')

      // 1) tentative backend Piper (audio réel)
      try {
        const res = await fetch(ttsUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: clean, tone: tone ?? 'neutral' }),
        })
        if (res.ok && (res.headers.get('content-type') || '').includes('audio')) {
          const buf = await res.arrayBuffer()
          if (token !== activeRef.current) return
          const Ctx =
            window.AudioContext ||
            (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
          const ctx = audioCtxRef.current ?? new Ctx()
          audioCtxRef.current = ctx
          if (ctx.state !== 'running') await ctx.resume()
          const audio = await ctx.decodeAudioData(buf)
          if (import.meta.env.DEV)
            console.debug('[voice] playing edge audio', audio.duration.toFixed(2) + 's', tone ?? 'neutral')
          const src = ctx.createBufferSource()
          src.buffer = audio
          const analyser = ctx.createAnalyser()
          analyser.fftSize = 1024
          const gain = ctx.createGain()
          gain.gain.value = 1
          src.connect(analyser)
          analyser.connect(gain)
          gain.connect(ctx.destination)
          analyserRef.current = analyser
          sourceRef.current = src
          setStatus('speaking')
          runRealLevel(token)
          src.onended = () => {
            if (token !== activeRef.current) return
            stopLevelLoop()
            levelRef.current = 0
            setLevel(0)
            setStatus('idle')
          }
          src.start()
          return
        }
      } catch {
        /* backend indisponible : voix navigateur */
      }

      if (token !== activeRef.current) return
      if (import.meta.env.DEV) console.debug('[voice] fallback browser voice')
      speakBrowser(clean, token)
    },
    [runRealLevel, speakBrowser, stopLevelLoop, ttsUrl],
  )

  speakRef.current = speak

  // déblocage audio à la première interaction
  useEffect(() => {
    const unlock = async () => {
      if (unlockedRef.current) return
      unlockedRef.current = true
      setNeedsGesture(false)
      if (import.meta.env.DEV) console.debug('[voice] unlocked by gesture')
      try {
        const Ctx =
          window.AudioContext ||
          (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
        const ctx = audioCtxRef.current ?? new Ctx()
        audioCtxRef.current = ctx
        if (ctx.state !== 'running') await ctx.resume()
      } catch {
        /* ignore */
      }
      const pending = pendingRef.current
      pendingRef.current = null
      if (import.meta.env.DEV) console.debug('[voice] pending at unlock:', pending ? pending.text.slice(0, 40) : 'none')
      if (pending && !mutedRef.current) void speakRef.current(pending.text, pending.tone)
    }
    const events: (keyof WindowEventMap)[] = ['pointerdown', 'touchstart', 'keydown']
    events.forEach((e) => window.addEventListener(e, unlock))
    return () => events.forEach((e) => window.removeEventListener(e, unlock))
  }, [])

  useEffect(() => () => stop(), [stop])

  return { speak, stop, status, speaking: status === 'speaking', level, levelRef, muted, setMuted, needsGesture }
}
