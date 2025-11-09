import { motion } from "motion/react";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "../ui/card";
import { TherapyBadge } from "../atoms/TherapyBadge";
import { LucideIcon } from "lucide-react";
import { ImageWithFallback } from "../figma/ImageWithFallback";

interface TherapyCardProps {
  title: string;
  description: string;
  icon: LucideIcon;
  image: string;
  category: string;
  categoryLabel: string;
  onDetailsClick?: () => void;
}

export function TherapyCard({
  title,
  description,
  icon: Icon,
  image,
  category,
  categoryLabel,
  onDetailsClick,
}: TherapyCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
      whileHover={{ y: -8 }}
    >
      <Card className="overflow-hidden h-full flex flex-col backdrop-blur-sm bg-card/80 border-border/50 shadow-lg hover:shadow-xl transition-all duration-300">
        <div className="relative h-48 overflow-hidden">
          <ImageWithFallback
            src={image}
            alt={title}
            className="w-full h-full object-cover transition-transform duration-500 hover:scale-110"
          />
          <div className="absolute top-3 right-3">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs bg-white/90 dark:bg-black/90 text-foreground backdrop-blur-sm shadow-lg">
              {categoryLabel}
            </span>
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-black/60 to-transparent" />
        </div>
        
        <CardHeader className="space-y-3">
          <div className="flex items-start gap-3">
            <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
              <Icon className="w-6 h-6" />
            </div>
            <CardTitle className="flex-1">{title}</CardTitle>
          </div>
        </CardHeader>
        
        <CardContent className="flex-1">
          <CardDescription className="leading-relaxed text-muted-foreground">
            {description}
          </CardDescription>
        </CardContent>
        
        <CardFooter>
          <Button 
            onClick={onDetailsClick} 
            className="w-full bg-primary hover:bg-primary/90 text-primary-foreground transition-all duration-300"
          >
            Ver detalles
          </Button>
        </CardFooter>
      </Card>
    </motion.div>
  );
}
