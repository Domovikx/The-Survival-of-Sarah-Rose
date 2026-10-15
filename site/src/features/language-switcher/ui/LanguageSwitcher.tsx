import * as stylex from '@stylexjs/stylex'
import { useTranslation } from 'react-i18next'

import { LANGS, setLang, type Lang } from '@/shared/config'

const styles = stylex.create({
  switcher: {
    display: 'inline-flex',
    border: '1px solid var(--border)',
    borderRadius: 8,
    overflow: 'hidden',
  },
  item: {
    appearance: 'none',
    border: 'none',
    background: 'transparent',
    color: 'var(--muted)',
    font: 'inherit',
    fontWeight: 600,
    fontSize: 13,
    padding: '4px 10px',
    cursor: 'pointer',
    minWidth: 40,
    minHeight: 30,
  },
  itemActive: {
    background: 'var(--panel-2)',
    color: 'var(--text)',
  },
})

export const LanguageSwitcher = () => {
  const { i18n, t } = useTranslation()
  const current = i18n.resolvedLanguage

  return (
    <div
      className={stylex.props(styles.switcher).className}
      role="group"
      aria-label={t('header.langLabel')}
    >
      {LANGS.map((lang) => {
        const sx = stylex.props(styles.item, current === lang && styles.itemActive)
        return (
          <button
            key={lang}
            type="button"
            className={sx.className}
            aria-pressed={current === lang}
            data-testid={`lang-${lang}`}
            onClick={() => setLang(lang as Lang)}
          >
            {lang.toUpperCase()}
          </button>
        )
      })}
    </div>
  )
}
