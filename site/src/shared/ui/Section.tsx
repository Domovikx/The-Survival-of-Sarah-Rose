import * as stylex from '@stylexjs/stylex'
import type { PropsWithChildren } from 'react'

import { Container } from './Container'

const styles = stylex.create({
  section: {
    paddingTop: 12,
    paddingBottom: 12,
  },
  title: {
    fontSize: 'clamp(20px, 3vw, 26px)',
    margin: '36px 0 12px',
    paddingBottom: 8,
    borderBottom: '1px solid var(--border)',
  },
})

type SectionProps = PropsWithChildren<{ title?: string }>

export const Section = ({ title, children }: SectionProps) => (
  <section className={stylex.props(styles.section).className}>
    <Container>
      {title ? <h2 className={stylex.props(styles.title).className}>{title}</h2> : null}
      {children}
    </Container>
  </section>
)
