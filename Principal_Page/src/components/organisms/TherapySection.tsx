import { motion } from "motion/react";
import { LucideIcon } from "lucide-react";

interface TherapySectionProps {
  id: string;
  title: string;
  subtitle: string;
  icon: LucideIcon;
  accentColor: string;
  children: React.ReactNode;
}

export function TherapySection({
  id,
  title,
  subtitle,
  icon: Icon,
  accentColor,
  children,
}: TherapySectionProps) {
  return (
    <section id={id} className="py-20 relative overflow-hidden">
      {/* Background Gradient */}
      <div className={`absolute inset-0 bg-gradient-to-br ${accentColor} opacity-5 dark:opacity-10`} />
      
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
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
            <Icon className="w-8 h-8 text-primary" />
          </motion.div>
          
          <h2 className="text-3xl md:text-4xl text-foreground mb-4">
            {title}
          </h2>
          
          <div className="w-20 h-1 bg-primary rounded-full mx-auto mb-6" />
          
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            {subtitle}
          </p>
        </motion.div>

        {/* Content Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {children}
        </div>
      </div>
    </section>
  );
}
