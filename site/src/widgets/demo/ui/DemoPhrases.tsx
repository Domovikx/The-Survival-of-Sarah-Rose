import * as stylex from '@stylexjs/stylex'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { Section } from '@/shared/ui'

// uid = md5(old) — файлы site/public/demo/{ru,en}/{uid}.mp3 (конвертация из
// ai_voice/**/*.opus, 5 цепляющих реплик, одинаковые uid в обоих языках).
const PHRASE_UIDS = [
  'e5d1a5b892d5f229deb5de98479c5a54',
  'f7ce26c09f2eae1a71e88764bc424281',
  'd0b1e33111292ed0c9523c4163d1b86e',
  '4cbde967290424a6402b1d1d852a4d7c',
  'bcd1cf9e4c99ac6da66f22cbe9326b74',
] as const

type Phrase = { speaker: string; text: string }

const styles = stylex.create({
  lead: {
    color: 'var(--muted)',
    margin: '0 0 16px',
    maxWidth: 720,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
    gap: 10,
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    gap: 14,
    backgroundColor: 'var(--panel)',
    borderWidth: 1,
    borderStyle: 'solid',
    borderColor: 'var(--border)',
    borderRadius: 12,
    padding: '12px 16px',
  },
  play: {
    appearance: 'none',
    border: 'none',
    borderRadius: '50%',
    width: 44,
    height: 44,
    flexShrink: 0,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    backgroundColor: 'var(--panel-2)',
    color: 'var(--text)',
    borderWidth: 1,
    borderStyle: 'solid',
    borderColor: 'var(--border)',
    transition: 'background-color 150ms ease, color 150ms ease, border-color 150ms ease, transform 150ms ease',
    ':hover': {
      borderColor: 'var(--link)',
      backgroundColor: 'var(--panel)',
    },
    ':active': { transform: 'scale(0.95)' },
    // Нейтральное кольцо: кнопка бывает красной (playing) — синий диссонировал бы
    ':focus-visible': { outline: '2px solid var(--text)', outlineOffset: 2 },
  },
  playOn: {
    backgroundColor: 'var(--accent)',
    borderColor: 'var(--accent)',
    color: '#ffffff',
  },
  body: {
    minWidth: 0,
  },
  text: {
    margin: 0,
    fontSize: 15,
    lineHeight: 1.45,
  },
  speaker: {
    fontSize: 13,
    color: 'var(--muted)',
    marginTop: 4,
    display: 'block',
  },
})

const PlayIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M8 5.5v13a1 1 0 0 0 1.53.85l10-6.5a1 1 0 0 0 0-1.7l-10-6.5A1 1 0 0 0 8 5.5z" />
  </svg>
)

const PauseIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <rect x="6" y="5" width="4" height="14" rx="1" />
    <rect x="14" y="5" width="4" height="14" rx="1" />
  </svg>
)

/**
 * Демо-фразы: 5 реплик с AI-озвучкой как крючок для скачивания.
 * Локаль определяет и текст, и аудио: RU-локаль → русские фразы, EN → английские.
 * Один проигрыватель на странице (новая фраза останавливает предыдущую).
 */
export const DemoPhrases = () => {
  const { t, i18n } = useTranslation()
  const lang = i18n.resolvedLanguage === 'ru' ? 'ru' : 'en'
  const phrases = t('demo.phrases', { returnObjects: true }) as Phrase[]
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [playing, setPlaying] = useState<string | null>(null)

  // Смена языка меняет и аудио — текущую фразу останавливаем.
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      setPlaying(null)
    }
  }, [lang])

  useEffect(() => () => audioRef.current?.pause(), [])

  const handlePlay = (uid: string) => {
    if (!audioRef.current) {
      const audio = new Audio()
      audio.addEventListener('ended', () => setPlaying(null))
      audioRef.current = audio
    }
    const audio = audioRef.current
    if (playing === uid) {
      audio.pause()
      setPlaying(null)
      return
    }
    audio.src = `${import.meta.env.BASE_URL}demo/${lang}/${uid}.mp3`
    audio.play().catch(() => setPlaying(null))
    setPlaying(uid)
  }

  return (
    <Section title={t('demo.title')} testId="demo">
      <p className={stylex.props(styles.lead).className} data-testid="demo-lead">
        {t('demo.lead')}
      </p>
      <div className={stylex.props(styles.grid).className} data-testid="demo-grid">
        {PHRASE_UIDS.map((uid, i) => {
          const phrase: Phrase | undefined = phrases[i]
          if (!phrase) return null
          const isPlaying = playing === uid
          return (
            <div
              key={uid}
              className={stylex.props(styles.row).className}
              data-testid={`demo-row-${i}`}
            >
              <button
                type="button"
                className={stylex.props(styles.play, isPlaying && styles.playOn).className}
                aria-label={
                  isPlaying
                    ? t('demo.pause', { name: phrase.speaker })
                    : t('demo.play', { name: phrase.speaker })
                }
                data-testid={`demo-play-${i}`}
                data-playing={isPlaying}
                onClick={() => handlePlay(uid)}
              >
                {isPlaying ? <PauseIcon /> : <PlayIcon />}
              </button>
              <div className={stylex.props(styles.body).className}>
                <p className={stylex.props(styles.text).className} data-testid={`demo-text-${i}`}>
                  {phrase.text}
                </p>
                <span
                  className={stylex.props(styles.speaker).className}
                  data-testid={`demo-speaker-${i}`}
                >
                  {phrase.speaker}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </Section>
  )
}
