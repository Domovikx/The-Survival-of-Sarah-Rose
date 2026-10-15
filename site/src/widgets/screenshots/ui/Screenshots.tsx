import * as stylex from '@stylexjs/stylex'
import { useTranslation } from 'react-i18next'

import { Section } from '@/shared/ui'

const SHOTS_BASE = `${import.meta.env.BASE_URL}shots/`

const styles = stylex.create({
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
    gap: 12,
  },
  figure: {
    margin: 0,
  },
  img: {
    width: '100%',
    height: 'auto',
    borderRadius: 10,
    borderWidth: 1,
    borderStyle: 'solid',
    borderColor: 'var(--border)',
    display: 'block',
  },
  caption: {
    fontSize: 13,
    color: 'var(--muted)',
    marginTop: 6,
  },
})

const SHOTS = [
  { file: 'main_menu_russian.jpg', capKey: 'shots.cap1', altKey: 'shots.cap1' },
  { file: 'dialogue_russian_1.jpg', capKey: 'shots.cap2', altKey: 'shots.cap2' },
  { file: 'language_settings_russian.jpg', capKey: 'shots.cap3', altKey: 'shots.cap3' },
  { file: 'dialogue_russian_2.jpg', capKey: 'shots.cap4', altKey: 'shots.cap4' },
] as const

export const Screenshots = () => {
  const { t } = useTranslation()

  return (
    <Section title={t('shots.title')} testId="screenshots">
      <div className={stylex.props(styles.grid).className} data-testid="screenshots-grid">
        {SHOTS.map((shot, i) => (
          <figure
            key={shot.file}
            className={stylex.props(styles.figure).className}
            data-testid={`screenshot-${i}`}
          >
            <img
              className={stylex.props(styles.img).className}
              src={`${SHOTS_BASE}${shot.file}`}
              alt={t(shot.altKey)}
              loading="lazy"
              data-testid={`screenshot-img-${i}`}
            />
            <figcaption
              className={stylex.props(styles.caption).className}
              data-testid={`screenshot-caption-${i}`}
            >
              {t(shot.capKey)}
            </figcaption>
          </figure>
        ))}
      </div>
    </Section>
  )
}
