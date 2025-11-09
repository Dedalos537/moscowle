import { motion } from "motion/react";
import { Star, Quote } from "lucide-react";

export function Testimonials() {
  const testimonials = [
    {
      name: "Liliana Carrión",
      role: "Madre de Familia",
      content: "A lo largo de todo este tiempo en lo que mi hijo ha asistido a las terapias, he visto un buen desarrollo en José Carlos tanto en el colegio como en su vida diaria. Estoy muy agradecida por el apoyo profesional.",
      rating: 5,
      avatar: "L",
    },
    {
      name: "Claudia Martínez",
      role: "Madre de Familia",
      content: "Tras estos 3 meses de terapia he notado que mi hijo se comporta de una forma más tranquila, más sociable. Todavía tiene algún que otro problema, pero ha mejorado bastante. El equipo es maravilloso.",
      rating: 5,
      avatar: "C",
    },
    {
      name: "Patricia Rodríguez",
      role: "Madre de Familia",
      content: "Mi hija ha aumentado bastante su vocabulario, utilizando palabras que antes no decía. Solo hacía emisiones de dos sílabas, aumentando su capacidad en este aspecto de manera impresionante.",
      rating: 5,
      avatar: "P",
    },
    {
      name: "María González",
      role: "Madre de Familia",
      content: "El centro ha sido fundamental en el desarrollo de mi hijo. Los terapeutas son muy profesionales y dedicados. Recomiendo ampliamente sus servicios a todas las familias.",
      rating: 5,
      avatar: "M",
    },
  ];

  return (
    <section className="py-20 relative overflow-hidden bg-gradient-to-br from-muted/30 via-background to-muted/30">
      {/* Decorative Elements */}
      <div className="absolute top-0 left-0 w-96 h-96 bg-accent/5 rounded-full blur-3xl" />
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
      
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <motion.div
            initial={{ scale: 0 }}
            whileInView={{ scale: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2, type: "spring" }}
            className="inline-flex items-center justify-center p-3 rounded-2xl bg-primary/10 mb-6"
          >
            <Quote className="w-8 h-8 text-primary" />
          </motion.div>
          
          <h2 className="text-3xl md:text-4xl text-foreground mb-4">
            Lo Que Dicen Nuestras Familias
          </h2>
          
          <div className="w-20 h-1 bg-primary rounded-full mx-auto mb-6" />
          
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            La confianza y satisfacción de nuestros pacientes son el mejor testimonio de nuestro compromiso y profesionalismo.
          </p>
        </motion.div>

        {/* Testimonials Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 md:gap-8">
          {testimonials.map((testimonial, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              whileHover={{ y: -8 }}
              className="group"
            >
              <div className="h-full p-8 rounded-2xl bg-card/80 backdrop-blur-sm border border-border/50 shadow-lg hover:shadow-xl hover:border-primary/50 transition-all duration-300">
                {/* Quote Icon */}
                <div className="mb-6">
                  <Quote className="w-10 h-10 text-primary/30 group-hover:text-primary/50 transition-colors duration-300" />
                </div>

                {/* Content */}
                <p className="text-muted-foreground leading-relaxed mb-6 italic">
                  "{testimonial.content}"
                </p>

                {/* Rating */}
                <div className="flex gap-1 mb-6">
                  {Array.from({ length: testimonial.rating }).map((_, i) => (
                    <Star key={i} className="w-5 h-5 text-primary fill-primary" />
                  ))}
                </div>

                {/* Author */}
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                    <span className="text-primary">{testimonial.avatar}</span>
                  </div>
                  <div>
                    <h4 className="text-foreground">
                      {testimonial.name}
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      {testimonial.role}
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
