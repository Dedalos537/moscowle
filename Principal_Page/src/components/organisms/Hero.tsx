import { motion } from "motion/react";
import { Heart, ArrowRight, Sparkles, Users, Brain, MessageCircle, Smile, Puzzle, Dna, Handshake } from "lucide-react";
import { Button } from "../ui/button";

export function Hero() {
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
                <Button size="lg" className="bg-primary hover:bg-primary/90 text-primary-foreground group">
                  Explorar Servicios
                  <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Button>
              </a>
              
              <a href="#contacto">
                <Button size="lg" variant="outline" className="border-primary/50 hover:bg-primary/5">
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
                      className="bg-background/80 backdrop-blur-sm rounded-2xl p-6 border border-border/50 hover:border-primary/50 transition-all duration-300 hover:shadow-lg"
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
