import * as stylex from '@stylexjs/stylex'
import { useTranslation } from 'react-i18next'

import { LINKS } from '@/shared/config'
import { Container } from '@/shared/ui'

const styles = stylex.create({
  footer: {
    marginTop: 48,
    borderTop: '1px solid var(--border)',
    padding: '18px 0 32px',
    color: 'var(--muted)',
    fontSize: 14,
  },
  links: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 12,
    margin: '10px 0 0',
    padding: 0,
    listStyle: 'none',
  },
})

export const Footer = () => {
  const { t } = useTranslation()

  return (
    <footer className={stylex.props(styles.footer).className}>
      <Container>
        <p>{t('footer.disclaimer')}</p>
        <ul className={stylex.props(styles.links).className} aria-label={t('footer.linksLabel')}>
          <li>
            <a href={LINKS.github}>{t('footer.linkGithub')}</a>
          </li>
          <li>
            <a href={LINKS.steam}>{t('footer.linkSteam')}</a>
          </li>
          <li>
            <a href={LINKS.issues}>{t('footer.linkIssues')}</a>
          </li>
          <li>
            <a href={LINKS.license}>{t('footer.linkLicense')}</a>
          </li>
          <li>
            <b>{t('footer.age')}</b>
          </li>
        </ul>
      </Container>
    </footer>
  )
}
