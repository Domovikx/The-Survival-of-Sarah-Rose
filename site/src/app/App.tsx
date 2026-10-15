import { Faq } from '@/widgets/faq'
import { Features } from '@/widgets/features'
import { Footer } from '@/widgets/footer'
import { Header } from '@/widgets/header'
import { Hero } from '@/widgets/hero'
import { Install } from '@/widgets/install'
import { Screenshots } from '@/widgets/screenshots'
import { VoiceStatus } from '@/widgets/voice-status'

export const App = () => (
  <>
    <Header />
    <main>
      <Hero />
      <Features />
      <VoiceStatus />
      <Install />
      <Screenshots />
      <Faq />
    </main>
    <Footer />
  </>
)
