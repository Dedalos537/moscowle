import { Heart, Facebook, Instagram, Linkedin, Mail } from "lucide-react";
import { motion } from "motion/react";

export function Footer() {
  const currentYear = new Date().getFullYear();
  
  const footerLinks = [
    {
      title: "Servicios",
      links: [
        { name: "Terapia Física", href: "#servicios" },
        { name: "Terapia Ocupacional", href: "#servicios" },
        { name: "Terapia del Lenguaje", href: "#servicios" },
        { name: "Apoyo Virtual", href: "#servicios" },
      ],
    },
    {
      title: "Información",
      links: [
        { name: "Acerca de Nosotros", href: "#acerca" },
        { name: "Nuestro Equipo", href: "#acerca" },
        { name: "Testimonios", href: "#acerca" },
        { name: "Blog", href: "#" },
      ],
    },
    {
      title: "Soporte",
      links: [
        { name: "Preguntas Frecuentes", href: "#" },
        { name: "Contacto", href: "#contacto" },
        { name: "Política de Privacidad", href: "#" },
        { name: "Términos y Condiciones", href: "#" },
      ],
    },
  ];

  const socialLinks = [
    { icon: Facebook, href: "#", label: "Facebook" },
    { icon: Instagram, href: "#", label: "Instagram" },
    { icon: Linkedin, href: "#", label: "LinkedIn" },
    { icon: Mail, href: "#contacto", label: "Email" },
  ];

  return (
    <footer className="relative bg-gradient-to-br from-foreground/95 to-foreground text-background overflow-hidden">
      {/* Decorative Elements */}
      <div className="absolute top-0 left-0 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-accent/10 rounded-full blur-3xl" />
      
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Main Footer Content */}
        <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-12 mb-12">
          {/* Brand Column */}
          <div className="lg:col-span-2">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="space-y-4"
            >
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-primary/20">
                  <Heart className="w-6 h-6 text-primary" fill="currentColor" />
                </div>
                <div className="flex flex-col">
                  <span className="text-primary">Centro de Terapias</span>
                  <span className="text-xs text-background/80">Juan Pablo II</span>
                </div>
              </div>
              
              <p className="text-sm text-background/80 leading-relaxed max-w-md">
                Más de 15 años brindando atención profesional y humana con terapias especializadas. 
                Tu bienestar es nuestra prioridad.
              </p>
              
              {/* Social Links */}
              <div className="flex gap-3 pt-2">
                {socialLinks.map((social, index) => (
                  <motion.a
                    key={index}
                    href={social.href}
                    aria-label={social.label}
                    whileHover={{ scale: 1.1, y: -2 }}
                    whileTap={{ scale: 0.95 }}
                    className="p-2.5 rounded-lg bg-primary/20 hover:bg-primary/30 text-background transition-colors duration-300"
                  >
                    <social.icon className="w-5 h-5" />
                  </motion.a>
                ))}
              </div>
            </motion.div>
          </div>

          {/* Links Columns */}
          {footerLinks.map((column, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
            >
              <h3 className="text-background mb-4">
                {column.title}
              </h3>
              <ul className="space-y-3">
                {column.links.map((link, linkIndex) => (
                  <li key={linkIndex}>
                    <a
                      href={link.href}
                      className="text-sm text-background/70 hover:text-primary transition-colors duration-300 inline-block hover:translate-x-1 transform"
                    >
                      {link.name}
                    </a>
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-background/10">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-sm text-background/70 text-center md:text-left">
              © {currentYear} Centro de Terapias Juan Pablo II. Todos los derechos reservados.
            </p>
            
            <div className="flex gap-6 text-sm text-background/70">
              <a href="#" className="hover:text-primary transition-colors duration-300">
                Privacidad
              </a>
              <a href="#" className="hover:text-primary transition-colors duration-300">
                Términos
              </a>
              <a href="#" className="hover:text-primary transition-colors duration-300">
                Cookies
              </a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
