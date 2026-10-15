import * as stylex from '@stylexjs/stylex'
import { useTranslation } from 'react-i18next'

import { Section } from '@/shared/ui'

const styles = stylex.create({
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
    gap: 14,
  },
  card: {
    background: 'var(--panel)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    padding: '16px 18px',
  },
  cardTitle: {
    fontSize: 17,
    margin: '0 0 6px',
  },
  cardText: {
    margin: 0,
    color: 'var(--muted)',
  },
})

const CARDS = [
  { icon: '🌐', titleKey: 'features.translateTitle', textKey: 'features.translateText' },
  { icon: '🎙', titleKey: 'features.voiceTitle', textKey: 'features.voiceText' },
  { icon: '🎭', titleKey: 'features.emotionTitle', textKey: 'features.emotionText' },
  { icon: '🗣', titleKey: 'features.voicesTitle', textKey: 'features.voicesText' },
] as const

export const Features = () => {
  const { t } = useTranslation()

  return (
    <Section title={t('features.title')}>
      <div className={stylex.props(styles.grid).className}>
        {CARDS.map((card) => (
          <div key={card.titleKey} className={stylex.props(styles.card).className}>
            <h3 className={stylex.props(styles.cardTitle).className}>
              {card.icon} {t(card.titleKey)}
            </h3>
            <p className={stylex.props(styles.cardText).className}>{t(card.textKey)}</p>
          </div>
        ))}
      </div>
    </Section>
  )
}
