import { useState, useEffect } from "react";
import { Navigation } from "./components/organisms/Navigation";
import { Hero } from "./components/organisms/Hero";
import { Stats } from "./components/organisms/Stats";
import { About } from "./components/organisms/About";
import { Testimonials } from "./components/organisms/Testimonials";
import { Contact } from "./components/organisms/Contact";
import { Footer } from "./components/organisms/Footer";
import { TherapyCard } from "./components/molecules/TherapyCard";
import { TherapyModal } from "./components/organisms/TherapyModal";
import { ScrollToTop } from "./components/atoms/ScrollToTop";
import { ServiceFilter, FilterCategory } from "./components/molecules/ServiceFilter";
import { motion } from "motion/react";
import { 
  BookOpen,
  Brain, 
  MessageCircle, 
  GraduationCap,
  Home,
  Puzzle,
  Target,
  Zap,
  Heart,
  Users,
  Video,
  BookMarked,
  Calculator,
  Lightbulb,
  Boxes,
  Type,
  Box,
  LucideIcon
} from "lucide-react";

interface SelectedTherapy {
  title: string;
  description: string;
  icon: LucideIcon;
  image: string;
  category: string;
  categoryLabel: string;
}

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [selectedTherapy, setSelectedTherapy] = useState<SelectedTherapy | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [activeFilter, setActiveFilter] = useState<FilterCategory>("all");

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [darkMode]);

  // Inicializar estado de autenticación desde localStorage
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) setIsLoggedIn(true);
  }, []);

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
  };

  const handleLogin = () => {
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_data');
    setIsLoggedIn(false);
    // opcional: redirigir a home
    try {
      window.location.assign('/');
    } catch (e) {
      window.location.href = '/';
    }
  };

  const handleTherapyClick = (therapy: SelectedTherapy) => {
    setSelectedTherapy(therapy);
    setModalOpen(true);
  };

  // Terapias Fundamentales
  const fundamentalTherapies = [
    {
      title: "Lecto-Escritura",
      description: "Potenciamos las habilidades de lectura y escritura, utilizando métodos innovadores y personalizados que utilizan desde recursos tangibles como libros sensoriales y material didáctico hasta software diseñado especialmente según a las necesidades del participante. Nuestro enfoque personalizado permite alcanzar grandes logros en el desempeño académico.",
      icon: BookOpen,
      image: "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=600&h=400&fit=crop",
      category: "Terapias" as const,
      categoryLabel: "Fundamental",
    },
    {
      title: "Conductual",
      description: "Terapia integral para tratar agresividad, impulsividad, ansiedad y depresión. Mejoramos la calidad de vida mediante modificación de conductas, siendo clave para el bienestar y desarrollo personal.",
      icon: Brain,
      image: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=600&h=400&fit=crop",
      category: "Terapias" as const,
      categoryLabel: "Fundamental",
    },
    {
      title: "De Lenguaje",
      description: "Ayudamos a personas con dificultades para hablar y comunicarse. Mediante técnicas personalizadas solucionamos problemas retraso en el desarrollo y trastornos del habla. Perfeccionando la producción de sonidos, incrementando el vocabulario, mejorando la estructura de oraciones y desarrollando el uso social del lenguaje para lograr una comunicación funcional y efectiva.",
      icon: MessageCircle,
      image: "https://images.unsplash.com/photo-1576267423445-b2e0074d68a4?w=600&h=400&fit=crop",
      category: "Terapias" as const,
      categoryLabel: "Fundamental",
    },
    {
      title: "De Aprendizaje",
      description: "Superamos dificultades de aprendizaje utilizando técnicas personalizadas para mejorar el rendimiento académico y habilidades cognitivas. Trabajamos con estrategias adaptadas a cada estilo individual.",
      icon: GraduationCap,
      image: "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=600&h=400&fit=crop",
      category: "Terapias" as const,
      categoryLabel: "Fundamental",
    },
    {
      title: "Ocupacional",
      description: "Superamos dificultades en actividades cotidianas como alimentación, higiene personal, control de esfínteres, estudio y recreación. Ofrecemos intervenciones personalizadas para fomentar la autosuficiencia.",
      icon: Home,
      image: "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=600&h=400&fit=crop",
      category: "Terapias" as const,
      categoryLabel: "Fundamental",
    },
  ];

  // Terapias Integrales
  const integralTherapies = [
    {
      title: "Autismo (TEA)",
      description: "Apoyo especializado para personas con Trastorno del Espectro Autista. Utilizamos técnicas propias para mejorar la comunicación, interacción social y adaptación al entorno, promoviendo el desarrollo integral.",
      icon: Puzzle,
      image: "https://images.unsplash.com/photo-1587654780291-39c9404d746b?w=600&h=400&fit=crop",
      category: "Terapias Integrales" as const,
      categoryLabel: "Integral",
    },
    {
      title: "TDA",
      description: "Tratamiento especializado para el Trastorno por Déficit de Atención. Mejoramos la concentración, organización y habilidades ejecutivas mediante técnicas terapéuticas personalizadas y estrategias efectivas.",
      icon: Target,
      image: "https://images.unsplash.com/photo-1606092195730-5d7b9af1efc5?w=600&h=400&fit=crop",
      category: "Terapias Integrales" as const,
      categoryLabel: "Integral",
    },
    {
      title: "TDAH",
      description: "Abordaje integral del Trastorno por Déficit de Atención e Hiperactividad. Combinamos estrategias conductuales y cognitivas para mejorar autocontrol, atención y habilidades sociales favoreciendo el éxito.",
      icon: Zap,
      image: "https://images.unsplash.com/photo-1551601651-2a8555f1a136?w=600&h=400&fit=crop",
      category: "Terapias Integrales" as const,
      categoryLabel: "Integral",
    },
    {
      title: "Síndrome de Down",
      description: "Apoyo especializado para personas con Síndrome de Down. Utilizamos técnicas propias para mejorar el desarrollo psicomotor, lenguaje y autonomía personal, potenciando todas sus capacidades individuales.",
      icon: Heart,
      image: "https://images.unsplash.com/photo-1544027993-37dbfe43562a?w=600&h=400&fit=crop",
      category: "Terapias Integrales" as const,
      categoryLabel: "Integral",
    },
    {
      title: "Discapacidad Intelectual",
      description: "Apoyo especializado para personas con cualquier tipo de Discapacidad Intelectual. Utilizamos técnicas innovadoras propias para fortalecer habilidades cognitivas, comunicación e independencia funcional.",
      icon: Users,
      image: "https://images.unsplash.com/photo-1609081219090-a6d81d3085bf?w=600&h=400&fit=crop",
      category: "Terapias Integrales" as const,
      categoryLabel: "Integral",
    },
  ];

  // Apoyo Virtual
  const virtualSupport = [
    {
      title: "Comunicación Oral",
      description: "Apoyo virtual especializado en desarrollo de habilidades de comunicación oral. Mejoramos la expresión verbal y comprensión auditiva de forma interactiva, personalizada y adaptada a cada necesidad.",
      icon: Video,
      image: "https://images.unsplash.com/photo-1577563908411-5077b6dc7624?w=600&h=400&fit=crop",
      category: "Apoyo Virtual" as const,
      categoryLabel: "Virtual",
    },
    {
      title: "Lecto-Escritura Virtual",
      description: "Método virtual innovador diseñado para fortalecer habilidades de lectura y escritura. Utilizamos plataformas digitales interactivas y ejercicios gamificados especializados.",
      icon: BookMarked,
      image: "https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=600&h=400&fit=crop",
      category: "Apoyo Virtual" as const,
      categoryLabel: "Virtual",
    },
    {
      title: "Matemáticas",
      description: "Apoyo virtual en matemáticas utilizando metodologías digitales propias e innovadoras. Facilitamos el aprendizaje de conceptos numéricos y operaciones matemáticas básicas y avanzadas de manera lúdica y efectiva.",
      icon: Calculator,
      image: "https://images.unsplash.com/photo-1509228468518-180dd4864904?w=600&h=400&fit=crop",
      category: "Apoyo Virtual" as const,
      categoryLabel: "Virtual",
    },
    {
      title: "Desarrollo Cognitivo",
      description: "Programa virtual para estimular y desarrollar funciones cognitivas superiores como memoria, atención, percepción y funciones ejecutivas. Utilizamos ejercicios especializados para resultados óptimos y efectivos integrales.",
      icon: Lightbulb,
      image: "https://images.unsplash.com/photo-1606092195730-5d7b9af1efc5?w=600&h=400&fit=crop",
      category: "Apoyo Virtual" as const,
      categoryLabel: "Virtual",
    },
  ];

  // Material Concreto
  const materialSupport = [
    {
      title: "Comunicación Oral",
      description: "Material para estimular y desarrollar habilidades de comunicación oral mediante juegos, tarjetas y actividades interactivas especializadas. Favorecemos la expresión verbal de manera tangible y práctica.",
      icon: Boxes,
      image: "https://images.unsplash.com/photo-1596464716127-f2a82984de30?w=600&h=400&fit=crop",
      category: "Material Concreto" as const,
      categoryLabel: "Material Didáctico",
    },
    {
      title: "Lecto-Escritura",
      description: "Recursos tangibles y manipulativos para aprendizaje de lectura y escritura. Incluimos letras móviles, libros sensoriales y material didáctico especializado de alta calidad para el desarrollo académico.",
      icon: Type,
      image: "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=600&h=400&fit=crop",
      category: "Material Concreto" as const,
      categoryLabel: "Material Didáctico",
    },
    {
      title: "Matemáticas",
      description: "Material manipulativo para aprendizaje de conceptos matemáticos, incluyendo ábacos, bloques lógicos, regletas y recursos didácticos concretos. Facilitamos la comprensión matemática mediante experiencias táctiles.",
      icon: Calculator,
      image: "https://images.unsplash.com/photo-1587620962725-abab7fe55159?w=600&h=400&fit=crop",
      category: "Material Concreto" as const,
      categoryLabel: "Material Didáctico",
    },
    {
      title: "Desarrollo Cognitivo",
      description: "Recursos físicos y tangibles para estimular el desarrollo cognitivo, incluyendo rompecabezas, juegos de memoria y material sensorial especializado. Promovemos el crecimiento cognitivo integral.",
      icon: Box,
      image: "https://images.unsplash.com/photo-1606092195730-5d7b9af1efc5?w=600&h=400&fit=crop",
      category: "Material Concreto" as const,
      categoryLabel: "Material Didáctico",
    },
  ];

  // Combinar todas las terapias
  const allTherapies = [
    ...fundamentalTherapies,
    ...integralTherapies,
    ...virtualSupport,
    ...materialSupport,
  ];

  // Filtrar terapias según el filtro activo
  const filteredTherapies = activeFilter === "all" 
    ? allTherapies 
    : allTherapies.filter(therapy => therapy.category === activeFilter);

  // Contar terapias por categoría
  const therapyCounts: Record<FilterCategory, number> = {
    all: allTherapies.length,
    "Terapias": fundamentalTherapies.length,
    "Terapias Integrales": integralTherapies.length,
    "Apoyo Virtual": virtualSupport.length,
    "Material Concreto": materialSupport.length,
  };

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-300">
      {/* Navigation */}
      <Navigation 
        darkMode={darkMode} 
        toggleDarkMode={toggleDarkMode}
        isLoggedIn={isLoggedIn}
        onLogin={handleLogin}
        onLogout={handleLogout}
      />

      {/* Hero Section */}
      <Hero />

      {/* Services Section */}
      <section id="servicios" className="relative py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-12"
          >
            <motion.div
              initial={{ scale: 0 }}
              whileInView={{ scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2, type: "spring" }}
              className="inline-flex items-center justify-center p-3 rounded-2xl bg-primary/10 mb-6"
            >
              <Heart className="w-8 h-8 text-primary" />
            </motion.div>
            
            <h2 className="text-3xl md:text-4xl text-foreground mb-4">
              Nuestros Servicios Especializados
            </h2>
            
            <div className="w-20 h-1 bg-primary rounded-full mx-auto mb-6" />
            
            <p className="text-lg text-muted-foreground max-w-3xl mx-auto leading-relaxed">
              Ofrecemos una amplia gama de terapias y servicios diseñados para atender las necesidades 
              únicas de cada persona con profesionalismo, calidez y experiencia.
            </p>
          </motion.div>

          {/* Filters */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="mb-12"
          >
            <ServiceFilter 
              activeFilter={activeFilter}
              onFilterChange={setActiveFilter}
              counts={therapyCounts}
            />
          </motion.div>

          {/* Therapies Grid */}
          <motion.div
            key={activeFilter}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8 "
          >
            {filteredTherapies.map((therapy, index) => (
              <motion.div
                key={`${therapy.category}-${index}`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
                className="h-full"
                data-therapy={therapy.title}
              >
                <TherapyCard 
                  {...therapy} 
                  onDetailsClick={() => handleTherapyClick(therapy)}
                />
              </motion.div>
            ))}
          </motion.div>

          {/* Empty State */}
          {filteredTherapies.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-20"
            >
              <p className="text-muted-foreground text-lg">
                No se encontraron servicios en esta categoría
              </p>
            </motion.div>
          )}
        </div>
      </section>

      {/* Removed Old Sections - Now integrated above */}
      {/* <section id="servicios" className="relative">
        <TherapySection
          id="terapias-fundamentales"
          title="Terapias Fundamentales"
          subtitle="Terapias especializadas para el desarrollo de habilidades específicas esenciales."
          icon={Brain}
          accentColor="from-primary/10 to-transparent"
        >
          {fundamentalTherapies.map((therapy, index) => (
            <TherapyCard 
              key={index} 
              {...therapy} 
              onDetailsClick={() => handleTherapyClick(therapy)}
            />
          ))}
        </TherapySection>

      </section> */}

      {/* Stats Section */}
      <Stats />

      {/* About Section */}
      <About />

      {/* Testimonials Section */}
      <Testimonials />

      {/* Contact Section */}
      <Contact />

      {/* Footer */}
      <Footer />

      {/* Scroll to Top Button */}
      <ScrollToTop />

      {/* Therapy Modal */}
      {selectedTherapy && (
        <TherapyModal
          open={modalOpen}
          onOpenChange={setModalOpen}
          title={selectedTherapy.title}
          description={selectedTherapy.description}
          icon={selectedTherapy.icon}
          image={selectedTherapy.image}
          category={selectedTherapy.category}
          categoryLabel={selectedTherapy.categoryLabel}
        />
      )}
    </div>
  );
}
