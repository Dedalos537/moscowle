import { motion } from "motion/react";
import { Users, Clock, Award, Heart } from "lucide-react";

export function Stats() {
  const stats = [
    {
      icon: Clock,
      value: "20+",
      label: "Años de Experiencia",
      description: "Trayectoria consolidada",
      color: "text-primary",
      bgColor: "bg-primary/10",
    },
    {
      icon: Users,
      value: "2000+",
      label: "Pacientes Atendidos",
      description: "Vidas transformadas",
      color: "text-secondary",
      bgColor: "bg-secondary/10",
    },
    {
      icon: Award,
      value: "98%",
      label: "Satisfacción",
      description: "Familias satisfechas",
      color: "text-accent",
      bgColor: "bg-accent/10",
    },
    {
      icon: Heart,
      value: "100%",
      label: "Dedicación",
      description: "Compromiso profesional",
      color: "text-primary",
      bgColor: "bg-primary/10",
    },
  ];

  return (
    <section className="py-20 relative overflow-hidden bg-gradient-to-br from-foreground/95 to-foreground text-background">
      {/* Decorative Elements */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-primary/20 rounded-full blur-3xl" />
      <div className="absolute bottom-0 left-0 w-96 h-96 bg-accent/20 rounded-full blur-3xl" />
      
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl text-background mb-4">
            Resultados Que Hablan Por Sí Mismos
          </h2>
          
          <div className="w-20 h-1 bg-primary rounded-full mx-auto mb-6" />
          
          <p className="text-lg text-background/80 max-w-2xl mx-auto leading-relaxed">
            Nuestra trayectoria y el bienestar de nuestros pacientes son el mejor testimonio de nuestro compromiso.
          </p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8">
          {stats.map((stat, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20, scale: 0.9 }}
              whileInView={{ opacity: 1, y: 0, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              whileHover={{ y: -8, scale: 1.05 }}
              className="group"
            >
              <div className="text-center p-8 rounded-2xl bg-background/10 backdrop-blur-sm border border-background/20 hover:bg-background/15 hover:border-primary/50 transition-all duration-300">
                <motion.div
                  initial={{ scale: 0 }}
                  whileInView={{ scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.3 + index * 0.1, type: "spring" }}
                  className={`inline-flex items-center justify-center p-4 rounded-2xl ${stat.bgColor} mb-4`}
                >
                  <stat.icon className={`w-8 h-8 ${stat.color}`} />
                </motion.div>
                
                <motion.div
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.5 + index * 0.1 }}
                  className="text-4xl md:text-5xl text-background mb-2"
                >
                  {stat.value}
                </motion.div>
                
                <h3 className="text-xl text-background mb-2">
                  {stat.label}
                </h3>
                
                <p className="text-sm text-background/70">
                  {stat.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
