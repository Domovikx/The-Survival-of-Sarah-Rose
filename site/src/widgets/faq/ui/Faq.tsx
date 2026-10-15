import * as stylex from '@stylexjs/stylex'
import { useTranslation } from 'react-i18next'

import { LINKS } from '@/shared/config'
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
  qa: {
    margin: '10px 0',
  },
  q: {
    margin: '0 0 4px',
    fontSize: 16,
  },
  a: {
    margin: 0,
    color: 'var(--muted)',
  },
})

export const Faq = () => {
  const { t } = useTranslation()

  return (
    <Section title={t('faq.title')}>
      <div className={stylex.props(styles.panel).className}>
        <div className={stylex.props(styles.qa).className}>
          <h3 className={stylex.props(styles.q).className}>{t('faq.q1')}</h3>
          <p className={stylex.props(styles.a).className}>{t('faq.a1')}</p>
        </div>
        <div className={stylex.props(styles.qa).className}>
          <h3 className={stylex.props(styles.q).className}>{t('faq.q2')}</h3>
          <p className={stylex.props(styles.a).className}>{t('faq.a2')}</p>
        </div>
        <div className={stylex.props(styles.qa).className}>
          <h3 className={stylex.props(styles.q).className}>{t('faq.q3')}</h3>
          <p className={stylex.props(styles.a).className}>
            {t('faq.a3')} <a href={LINKS.license}>{t('footer.linkLicense')}</a>
          </p>
        </div>
        <div className={stylex.props(styles.qa).className}>
          <h3 className={stylex.props(styles.q).className}>{t('faq.q4')}</h3>
          <p className={stylex.props(styles.a).className}>
            {t('faq.a4')} <a href={LINKS.github}>{t('footer.linkGithub')}</a>
          </p>
        </div>
      </div>
    </Section>
  )
}
