import React, { useCallback } from "react";
import { motion } from "motion/react";
import { Heart, ArrowRight, Sparkles, Users, Brain, MessageCircle, Smile, Puzzle, Dna, Handshake } from "lucide-react";
import { Button } from "../ui/button";

export function Hero() {
  const getBorderColor = (colorClass: string) => {
    try {
      const root = getComputedStyle(document.documentElement);
      switch (colorClass) {
        case "text-primary":
          return root.getPropertyValue("--primary").trim() || "#81A141";
        case "text-accent":
          return root.getPropertyValue("--accent").trim() || "#5e7f2a";
        case "text-secondary":
          return root.getPropertyValue("--secondary").trim() || "#dfe77c";
        default:
          return root.getPropertyValue("--primary").trim() || "#81A141";
      }
    } catch (e) {
      return "#81A141";
    }
  };

  const hexToRgba = (hex: string, alpha = 1) => {
    if (!hex) return `rgba(129,161,65,${alpha})`;
    const h = hex.replace('#','').trim();
    if (h.startsWith('rgb')) {
      // already rgb/rgba string
      return hex;
    }
    if (h.length === 3) {
      const r = parseInt(h[0]+h[0], 16);
      const g = parseInt(h[1]+h[1], 16);
      const b = parseInt(h[2]+h[2], 16);
      return `rgba(${r},${g},${b},${alpha})`;
    }
    if (h.length === 6) {
      const r = parseInt(h.substring(0,2), 16);
      const g = parseInt(h.substring(2,4), 16);
      const b = parseInt(h.substring(4,6), 16);
      return `rgba(${r},${g},${b},${alpha})`;
    }
    return hex;
  };

  const handleHeroFocus = useCallback((label: string) => {
    if (!label) return;
    const nodes = Array.from(document.querySelectorAll('[data-therapy]')) as HTMLElement[];
    if (!nodes.length) return;

    const normalize = (s: string) =>
      s
        .toLowerCase()
        .normalize('NFD')
        .replace(/\p{Diacritic}/gu, '')
        .replace(/[^a-z0-9\s]/g, '')
        .trim();

    const query = normalize(label);

    // First try: exact includes (normalized)
    let target: HTMLElement | undefined = nodes.find(n => {
      const t = normalize(n.getAttribute('data-therapy') || '');
      return t.includes(query);
    });

    // Second try: exact word-start match
    if (!target) {
      target = nodes.find(n => {
        const t = normalize(n.getAttribute('data-therapy') || '');
        return t.split(' ').some(w => query.startsWith(w) || w.startsWith(query));
      });
    }

    // Third: scoring by number of overlapping words (simple fuzzy match)
    if (!target) {
      const qWords = new Set(query.split(/\s+/).filter(Boolean));
      let best: { node: HTMLElement; score: number } | null = null;
      for (const n of nodes) {
        const t = normalize(n.getAttribute('data-therapy') || '');
        const words = new Set(t.split(/\s+/).filter(Boolean));
        let score = 0;
        for (const w of qWords) if (words.has(w)) score++;
        if (!best || score > best.score) best = { node: n, score };
      }
      if (best && best.score > 0) target = best.node;
    }

    if (!target) target = nodes[0];

    const el = target as HTMLElement;

    // Scroll into view but account for sticky header if present
    const header = document.querySelector('header, nav, [data-header]') as HTMLElement | null;
    const headerHeight = header ? header.getBoundingClientRect().height : 84; // reasonable default
    const rect = el.getBoundingClientRect();
    const top = rect.top + window.scrollY - headerHeight - 24; // small offset
    window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });

    // try to find the inner Card element to apply the neon highlight flush to the card border
    const cardEl = el.querySelector('[data-slot="card"]') as HTMLElement | null;
    const color = getBorderColor(itemColorFromLabel(label));
    const rgba = hexToRgba(color, 0.26);
    const HIGHLIGHT_MS = 1500; // 1.5s bounce preview

    if (cardEl) {
      // Prefer Web Animations API for a reliable bounce (works even when other transforms exist)
      try {
        if (cardEl.animate) {
          const keyframes = [
            { transform: 'translateY(0) scale(1)' },
            { transform: 'translateY(-12px) scale(1.02)' },
            { transform: 'translateY(0) scale(0.995)' },
            { transform: 'translateY(-6px) scale(1.01)' },
            { transform: 'translateY(0) scale(1)' },
          ];
          const anim = cardEl.animate(keyframes, { duration: HIGHLIGHT_MS, easing: 'cubic-bezier(.22,.9,.35,1)', fill: 'both' });
          // ensure removal of any fallback class if present
          cardEl.classList.remove('card-bounce');
          // no further cleanup required; animation will end naturally
        } else {
          // fallback to CSS class if Web Animations API not available
          cardEl.classList.add('card-bounce');
          // ensure reflow so animation starts reliably
          // eslint-disable-next-line @typescript-eslint/no-unused-expressions
          cardEl.offsetHeight;
          setTimeout(() => {
            cardEl.classList.remove('card-bounce');
          }, HIGHLIGHT_MS);
        }
      } catch (e) {
        // final fallback: CSS class
        cardEl.classList.add('card-bounce');
        // eslint-disable-next-line @typescript-eslint/no-unused-expressions
        cardEl.offsetHeight;
        setTimeout(() => cardEl.classList.remove('card-bounce'), HIGHLIGHT_MS);
      }
    } else {
      // fallback: briefly add bounce to wrapper element
      if ((el as HTMLElement).animate) {
        try {
          (el as HTMLElement).animate([
            { transform: 'translateY(0) scale(1)' },
            { transform: 'translateY(-12px) scale(1.02)' },
            { transform: 'translateY(0) scale(0.995)' },
            { transform: 'translateY(-6px) scale(1.01)' },
            { transform: 'translateY(0) scale(1)' },
          ], { duration: HIGHLIGHT_MS, easing: 'cubic-bezier(.22,.9,.35,1)', fill: 'both' });
        } catch (e) {
          el.classList.add('card-bounce');
          // eslint-disable-next-line @typescript-eslint/no-unused-expressions
          el.offsetHeight;
          setTimeout(() => el.classList.remove('card-bounce'), HIGHLIGHT_MS);
        }
      } else {
        el.classList.add('card-bounce');
        // eslint-disable-next-line @typescript-eslint/no-unused-expressions
        el.offsetHeight;
        setTimeout(() => el.classList.remove('card-bounce'), HIGHLIGHT_MS);
      }
    }
  }, []);

  // heuristic: choose color by matching label to known items
  function itemColorFromLabel(label: string) {
    const l = label.toLowerCase();
    if (l.includes('social') || l.includes('habil') ) return 'text-primary';
    if (l.includes('aprendiz') || l.includes('matem') ) return 'text-accent';
    if (l.includes('lenguaje') || l.includes('comunic') ) return 'text-primary';
    if (l.includes('conduct') ) return 'text-secondary';
    if (l.includes('tea') ) return 'text-accent';
    if (l.includes('down') ) return 'text-primary';
    return 'text-primary';
  }
  return (
    <section id="inicio" className="relative min-h-screen flex items-center pt-16 overflow-hidden">
      {/* Gradient Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-background to-secondary/10 dark:from-primary/10 dark:via-background dark:to-secondary/5" />
      
      {/* Decorative Elements */}
      <div className="absolute top-20 right-10 w-72 h-72 bg-primary/10 rounded-full blur-3xl animate-pulse" />
      <div className="absolute bottom-20 left-10 w-96 h-96 bg-accent/10 rounded-full blur-3xl animate-pulse delay-1000" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          {/* Content */}
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8 }}
            className="space-y-8"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: "spring" }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary"
            >
              <Sparkles className="w-4 h-4" />
              <span className="text-sm">Esperanza y Bienestar</span>
            </motion.div>

            <div className="space-y-4">
              <h1 className="text-4xl md:text-5xl lg:text-6xl text-foreground">
                Centro de Terapias
                <span className="block text-primary mt-2">Juan Pablo II</span>
              </h1>
              
              <p className="text-lg text-muted-foreground leading-relaxed max-w-xl">
                Brindamos atención personalizada con terapias especializadas, integrales y apoyo virtual. 
                Un espacio de sanación, crecimiento y esperanza para ti y tu familia.
              </p>
            </div>

            <div className="flex flex-wrap gap-4">
              <a href="#servicios">
                <Button size="lg" className="bg-primary hover:bg-primary/90 text-primary-foreground group" attention attentionInterval={9000}>
                  Explorar Servicios
                  <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Button>
              </a>
              
              <a href="#contacto">
                <Button size="lg" variant="outline" className="border-primary/50 hover:bg-primary/5" attention attentionInterval={12000}>
                  Contáctanos
                </Button>
              </a>
            </div>

            {/* Stats */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="grid grid-cols-3 gap-6 pt-8"
            >
              {[
                { value: "20+", label: "Años de experiencia" },
                { value: "2000+", label: "Pacientes atendidos" },
                { value: "98%", label: "Satisfacción" },
              ].map((stat, index) => (
                <div key={index} className="text-center">
                  <div className="text-2xl md:text-3xl text-primary">{stat.value}</div>
                  <div className="text-xs md:text-sm text-muted-foreground mt-1">{stat.label}</div>
                </div>
              ))}
            </motion.div>
          </motion.div>

          {/* Image/Illustration */}
          <motion.div
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="relative"
          >
            <div className="relative aspect-square max-w-lg mx-auto">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/20 to-accent/20 rounded-3xl blur-2xl" />
              <div className="relative bg-card/50 backdrop-blur-sm border border-border/50 rounded-3xl p-8 shadow-2xl">
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { icon: Users, label: "Habilidades Sociales", color: "text-primary" },
                    { icon: Brain, label: "Terapia Aprendizaje", color: "text-accent" },
                    { icon: MessageCircle, label: "Terapia de Lenguaje", color: "text-primary" },
                    { icon: Smile, label: "Terapia Conductual", color: "text-secondary" },
                    { icon: Handshake, label: "Terapia para TEA", color: "text-accent" },
                    { icon: Heart, label: "Terapia para Down", color: "text-primary" },
                  ].map((item, index) => (
                    <motion.div
                      key={index}
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.8 + index * 0.1, type: "spring" }}
                      className="bg-background/80 backdrop-blur-sm rounded-2xl p-6 border transition-all duration-300 hover:shadow-lg cursor-pointer"
                      style={{ borderColor: getBorderColor(item.color) }}
                      onClick={() => handleHeroFocus(item.label)}
                    >
                      <item.icon className={`w-8 h-8 ${item.color} mb-3`} />
                      <p className="text-sm text-foreground/80">{item.label}</p>
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
