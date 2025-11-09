import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import { LucideIcon } from "lucide-react";
import { Button } from "../ui/button";
import { ImageWithFallback } from "../figma/ImageWithFallback";
import { motion } from "motion/react";
import { CheckCircle2, Clock, Users, Target, Phone } from "lucide-react";
import { Separator } from "../ui/separator";

interface TherapyModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  icon: LucideIcon;
  image: string;
  category: string;
  categoryLabel: string;
  benefits?: string[];
}

export function TherapyModal({
  open,
  onOpenChange,
  title,
  description,
  icon: Icon,
  image,
  category,
  categoryLabel,
  benefits = [
    "Atención personalizada y profesional",
    "Evaluación inicial completa",
    "Plan de tratamiento individualizado",
    "Seguimiento continuo del progreso",
    "Comunicación constante con familiares",
    "Materiales y recursos especializados",
  ],
}: TherapyModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-start justify-between gap-4 mb-2">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-2xl bg-primary/10 text-primary">
                <Icon className="w-8 h-8" />
              </div>
              <div>
                <DialogTitle className="text-2xl md:text-3xl">{title}</DialogTitle>
                <span className="inline-block mt-1 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs">
                  {categoryLabel}
                </span>
              </div>
            </div>
          </div>
        </DialogHeader>
        
        <div className="space-y-6">
          {/* Image */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
            className="relative h-64 md:h-80 rounded-2xl overflow-hidden"
          >
            <ImageWithFallback
              src={image}
              alt={title}
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
            <div className="absolute bottom-6 left-6 right-6">
              <h4 className="text-white text-xl md:text-2xl mb-2">Terapia Profesional Especializada</h4>
              <p className="text-white/90 text-sm">Centro de Terapias Juan Pablo II</p>
            </div>
          </motion.div>

          {/* Description */}
          <div className="prose prose-sm max-w-none">
            <DialogDescription className="text-base leading-relaxed text-muted-foreground">
              {description}
            </DialogDescription>
          </div>

          <Separator />

          {/* Quick Info */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-muted/50 text-center">
              <Clock className="w-5 h-5 text-primary mx-auto mb-2" />
              <div className="text-sm text-foreground">Duración</div>
              <div className="text-xs text-muted-foreground mt-1">45-60 min</div>
            </div>
            <div className="p-4 rounded-xl bg-muted/50 text-center">
              <Users className="w-5 h-5 text-primary mx-auto mb-2" />
              <div className="text-sm text-foreground">Modalidad</div>
              <div className="text-xs text-muted-foreground mt-1">Individual</div>
            </div>
            <div className="p-4 rounded-xl bg-muted/50 text-center">
              <Target className="w-5 h-5 text-primary mx-auto mb-2" />
              <div className="text-sm text-foreground">Enfoque</div>
              <div className="text-xs text-muted-foreground mt-1">Personalizado</div>
            </div>
            <div className="p-4 rounded-xl bg-muted/50 text-center">
              <Phone className="w-5 h-5 text-primary mx-auto mb-2" />
              <div className="text-sm text-foreground">Consulta</div>
              <div className="text-xs text-muted-foreground mt-1">Disponible</div>
            </div>
          </div>

          <Separator />

          {/* Benefits */}
          <div>
            <h3 className="text-xl text-foreground mb-4 flex items-center gap-2">
              <CheckCircle2 className="w-6 h-6 text-primary" />
              Beneficios del Tratamiento
            </h3>
            <div className="grid sm:grid-cols-2 gap-3">
              {benefits.map((benefit, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                  className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                >
                  <CheckCircle2 className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
                  <span className="text-sm text-muted-foreground">{benefit}</span>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Additional Info */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20">
            <h4 className="text-foreground mb-2 flex items-center gap-2">
              <Target className="w-5 h-5 text-primary" />
              ¿Por qué elegirnos?
            </h4>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Contamos con más de 20 años de experiencia atendiendo a más de 1000 familias. 
              Nuestro equipo multidisciplinario de profesionales especializados trabaja con 
              metodologías innovadoras basadas en evidencia científica, garantizando resultados 
              efectivos y duraderos en cada tratamiento.
            </p>
          </div>

          {/* CTA */}
          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <Button
              className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg hover:shadow-xl transition-all"
              size="lg"
              onClick={() => {
                onOpenChange(false);
                const contactSection = document.getElementById("contacto");
                if (contactSection) {
                  contactSection.scrollIntoView({ behavior: "smooth" });
                }
              }}
            >
              <Phone className="w-4 h-4 mr-2" />
              Agendar Cita Ahora
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={() => onOpenChange(false)}
            >
              Cerrar
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
