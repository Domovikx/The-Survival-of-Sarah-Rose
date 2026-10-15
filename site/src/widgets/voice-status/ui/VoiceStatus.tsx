import * as stylex from '@stylexjs/stylex'
import { useTranslation } from 'react-i18next'

import { Section } from '@/shared/ui'

const styles = stylex.create({
  panel: {
    backgroundColor: 'var(--panel)',
    borderWidth: 1,
    borderStyle: 'solid',
    borderColor: 'var(--border)',
    borderRadius: 12,
    padding: '16px 18px',
  },
  total: {
    margin: '0 0 8px',
  },
  list: {
    margin: 0,
    paddingLeft: 20,
    color: 'var(--muted)',
  },
})

export const VoiceStatus = () => {
  const { t } = useTranslation()

  return (
    <Section title={t('voice.title')}>
      <div className={stylex.props(styles.panel).className}>
        <p className={stylex.props(styles.total).className}>
          <b>{t('voice.total')}</b>
        </p>
        <ul className={stylex.props(styles.list).className}>
          <li>{t('voice.ru')}</li>
          <li>{t('voice.en')}</li>
          <li>{t('voice.missing')}</li>
        </ul>
      </div>
    </Section>
  )
}
