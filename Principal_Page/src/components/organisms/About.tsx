import { motion } from "motion/react";
import { Target, Eye, Heart, Handshake, Lightbulb, Award, Users, ShieldCheck, CheckCircle } from "lucide-react";

export function About() {
  const values = [
    {
      icon: Heart,
      title: "Empatía",
      description: "Comprendemos y nos conectamos con las necesidades únicas de cada familia",
    },
    {
      icon: Handshake,
      title: "Respeto",
      description: "Valoramos la diversidad y dignidad de cada persona sin distinción",
    },
    {
      icon: Lightbulb,
      title: "Innovación",
      description: "Aplicamos metodologías actualizadas basadas en evidencia científica",
    },
    {
      icon: Award,
      title: "Excelencia",
      description: "Buscamos la mejora continua en todos nuestros servicios",
    },
    {
      icon: Users,
      title: "Trabajo en Equipo",
      description: "Colaboramos interdisciplinariamente para mejores resultados",
    },
    {
      icon: ShieldCheck,
      title: "Compromiso",
      description: "Dedicación absoluta al bienestar y desarrollo de nuestros niños",
    },
  ];

  return (
    <section id="acerca" className="py-20 relative overflow-hidden bg-gradient-to-br from-background via-muted/20 to-background">
      {/* Decorative Elements */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
      <div className="absolute bottom-0 left-0 w-96 h-96 bg-accent/5 rounded-full blur-3xl" />
      
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
            <Heart className="w-8 h-8 text-primary" fill="currentColor" />
          </motion.div>
          
          <h2 className="text-3xl md:text-4xl text-foreground mb-4">
            Acerca de Nosotros
          </h2>
          
          <div className="w-20 h-1 bg-primary rounded-full mx-auto mb-6" />
          
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto leading-relaxed">
            Centro especializado en terapias integrales para personas con habilidades diferentes. 
            Más de 20 años de experiencia transformando vidas con profesionalismo, calidez y esperanza.
          </p>
        </motion.div>

        {/* Misión y Visión */}
        <div className="grid lg:grid-cols-2 gap-8 mb-16">
          {/* Misión Card */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="group"
          >
            <div className="h-full p-8 md:p-10 rounded-3xl bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20 hover:border-primary/40 transition-all duration-300 shadow-lg hover:shadow-xl">
              <div className="flex items-start gap-4 mb-6">
                <div className="p-3 rounded-xl bg-primary/20 text-primary group-hover:scale-110 transition-transform duration-300">
                  <Target className="w-8 h-8" />
                </div>
                <div>
                  <h3 className="text-2xl md:text-3xl text-foreground mb-2">
                    Nuestra Misión
                  </h3>
                  <div className="w-16 h-1 bg-primary rounded-full" />
                </div>
              </div>
              
              <p className="text-muted-foreground leading-relaxed mb-6">
                Brindar una educación integral, inclusiva y de calidad a personas con habilidades diferentes, 
                potenciando sus capacidades cognitivas, emocionales y sociales a través de metodologías 
                innovadoras y un enfoque personalizado que respete su ritmo de aprendizaje y promueva 
                su autonomía e integración plena en la sociedad.
              </p>

              <div className="grid grid-cols-2 gap-4 pt-6 border-t border-primary/20">
                <div className="text-center">
                  <div className="text-3xl md:text-4xl text-primary mb-1">1000+</div>
                  <div className="text-sm text-muted-foreground">Familias Atendidas</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl md:text-4xl text-primary mb-1">20+</div>
                  <div className="text-sm text-muted-foreground">Años de Experiencia</div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Visión Card */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="group"
          >
            <div className="h-full p-8 md:p-10 rounded-3xl bg-gradient-to-br from-secondary/10 to-secondary/5 border border-secondary/20 hover:border-secondary/40 transition-all duration-300 shadow-lg hover:shadow-xl">
              <div className="flex items-start gap-4 mb-6">
                <div className="p-3 rounded-xl bg-secondary/20 text-secondary group-hover:scale-110 transition-transform duration-300">
                  <Eye className="w-8 h-8" />
                </div>
                <div>
                  <h3 className="text-2xl md:text-3xl text-foreground mb-2">
                    Nuestra Visión
                  </h3>
                  <div className="w-16 h-1 bg-secondary rounded-full" />
                </div>
              </div>
              
              <p className="text-muted-foreground leading-relaxed mb-6">
                Ser reconocidos como un centro educativo líder en la región, referente en la atención 
                especializada de personas con habilidades diferentes, caracterizado por su excelencia 
                académica, compromiso social y calidez humana, donde la diversidad de capacidades sea 
                valorada y respetada como una riqueza que enriquece a toda la comunidad.
              </p>

              <div className="space-y-3 pt-6 border-t border-secondary/20">
                <div className="flex items-center gap-3 text-muted-foreground">
                  <CheckCircle className="w-5 h-5 text-secondary flex-shrink-0" />
                  <span>Excelencia Académica</span>
                </div>
                <div className="flex items-center gap-3 text-muted-foreground">
                  <CheckCircle className="w-5 h-5 text-secondary flex-shrink-0" />
                  <span>Compromiso Social</span>
                </div>
                <div className="flex items-center gap-3 text-muted-foreground">
                  <CheckCircle className="w-5 h-5 text-secondary flex-shrink-0" />
                  <span>Calidez Humana</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Valores Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm mb-4">
            <Award className="w-4 h-4" />
            NUESTROS VALORES
          </span>
          <h3 className="text-2xl md:text-3xl text-foreground mb-3">
            Lo Que Nos <span className="text-primary">Define</span>
          </h3>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Principios que guían nuestro trabajo diario y nos comprometen con la excelencia
          </p>
        </motion.div>

        {/* Values Grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {values.map((value, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              whileHover={{ y: -8 }}
              className="group"
            >
              <div className="h-full p-6 rounded-2xl bg-card/80 backdrop-blur-sm border border-border/50 shadow-lg hover:shadow-xl hover:border-primary/50 transition-all duration-300 text-center">
                <div className="inline-flex p-4 rounded-2xl bg-primary/10 text-primary mb-4 group-hover:scale-110 group-hover:bg-primary/20 transition-all duration-300">
                  <value.icon className="w-7 h-7" />
                </div>
                
                <h4 className="text-foreground mb-2">
                  {value.title}
                </h4>
                
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {value.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
