import { motion } from "motion/react";
import { useRef, useEffect, useState } from "react";
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
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [isScrollable, setIsScrollable] = useState(false);
  const [showScrollIndicator, setShowScrollIndicator] = useState(true);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (container) {
      const checkScrollable = () => {
        setIsScrollable(container.scrollHeight > container.clientHeight);
      };
      
      checkScrollable();
      
      const handleScroll = () => {
        const isNearBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - 10;
        setShowScrollIndicator(!isNearBottom);
      };

      container.addEventListener('scroll', handleScroll);
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, [description]);
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      className="h-full"
      viewport={{ once: true }}
      transition={{ duration: 0.5 }}
      whileHover={{ y: -8 }}
      onClick={onDetailsClick}
    >
      <Card className="overflow-hidden h-full min-h-[500px] flex flex-col backdrop-blur-sm bg-card/80 border-border/50 shadow-lg hover:shadow-xl transition-all duration-300">
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
        
        <CardContent className="flex-1 relative min-h-0">
          <div 
            ref={scrollContainerRef}
            className="h-full overflow-y-auto scrollbar-thin scrollbar-thumb-primary/20 scrollbar-track-transparent hover:scrollbar-thumb-primary/40 transition-colors"
          >
            <CardDescription className="leading-relaxed text-muted-foreground pr-2">
              {description}
            </CardDescription>
          </div>
          {/* Scroll indicator gradient - only show when content is scrollable and not at bottom */}
          {isScrollable && showScrollIndicator && (
            <div className="absolute bottom-0 left-0 right-0 h-6 bg-gradient-to-t from-card via-card/80 to-transparent pointer-events-none transition-opacity duration-300" />
          )}
          {/* Subtle scroll hint */}
          {isScrollable && showScrollIndicator && (
            <div className="absolute bottom-1 right-2 text-xs text-muted-foreground/50 pointer-events-none">
              ⋯
            </div>
          )}
        </CardContent>
        
        <CardFooter className="mt-auto">
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
