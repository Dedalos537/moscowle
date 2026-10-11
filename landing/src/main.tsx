import '@fontsource-variable/bricolage-grotesque/opsz.css';
import '@fontsource/atkinson-hyperlegible-next/400.css';
import '@fontsource/atkinson-hyperlegible-next/700.css';
import './styles.css';

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { useContent } from './content';
import { About, Faq, Testimonials } from './sections/About';
import { Booking } from './sections/Booking';
import { Evaluation } from './sections/Evaluation';
import { Figures } from './sections/Figures';
import { Footer, MobileBar } from './sections/Footer';
import { Hero } from './sections/Hero';
import { Services } from './sections/Services';
import { TopBar } from './sections/TopBar';

function App() {
  const content = useContent();
  return (
    <>
      <a className="skip" href="#agendar">
        Ir a agendar la evaluación
      </a>
      <TopBar content={content} />
      <main id="inicio">
        <Hero content={content} />
        <Evaluation content={content} />
        <Services content={content} />
        <Figures content={content} />
        <About content={content} />
        <Testimonials content={content} />
        <Faq content={content} />
        <Booking content={content} />
      </main>
      <Footer content={content} />
      <MobileBar content={content} />
    </>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
