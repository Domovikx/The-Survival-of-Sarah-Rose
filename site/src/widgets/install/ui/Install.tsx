import * as stylex from '@stylexjs/stylex'
import { useTranslation } from 'react-i18next'

import { Section } from '@/shared/ui'

const styles = stylex.create({
  panel: {
    background: 'var(--panel)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    padding: '16px 22px',
  },
  list: {
    margin: '0 0 8px',
    paddingLeft: 22,
  },
  item: {
    margin: '6px 0',
  },
  note: {
    color: 'var(--muted)',
    fontSize: 14,
    margin: 0,
  },
})

export const Install = () => {
  const { t } = useTranslation()

  return (
    <Section title={t('install.title')}>
      <div className={stylex.props(styles.panel).className}>
        <ol className={stylex.props(styles.list).className}>
          <li className={stylex.props(styles.item).className}>{t('install.step1')}</li>
          <li className={stylex.props(styles.item).className}>{t('install.step2')}</li>
          <li className={stylex.props(styles.item).className}>{t('install.step3')}</li>
        </ol>
        <p className={stylex.props(styles.note).className}>{t('install.note')}</p>
      </div>
    </Section>
  )
}
