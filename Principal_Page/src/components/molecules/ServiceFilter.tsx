import { motion } from "motion/react";
import { Brain, Heart, Video, Box, LucideIcon } from "lucide-react";
import { Button } from "../ui/button";

export type FilterCategory = "all" | "Terapias" | "Terapias Integrales" | "Apoyo Virtual" | "Material Concreto";

interface ServiceFilterProps {
  activeFilter: FilterCategory;
  onFilterChange: (filter: FilterCategory) => void;
  counts: Record<FilterCategory, number>;
}

interface FilterOption {
  id: FilterCategory;
  name: string;
  icon: LucideIcon;
  color: string;
}

const filterOptions: FilterOption[] = [
  { id: "all", name: "Todos", icon: Brain, color: "text-primary" },
  { id: "Terapias", name: "Terapias Fundamentales", icon: Brain, color: "text-primary" },
  { id: "Terapias Integrales", name: "Terapias Integrales", icon: Heart, color: "text-secondary" },
  { id: "Apoyo Virtual", name: "Apoyo Virtual", icon: Video, color: "text-accent" },
  { id: "Material Concreto", name: "Material Didáctico", icon: Box, color: "text-muted-foreground" },
];

export function ServiceFilter({ activeFilter, onFilterChange, counts }: ServiceFilterProps) {
  return (
    <div className="w-full">
      {/* Desktop Filters */}
      <div className="hidden lg:flex items-center justify-center gap-4 flex-wrap">
        {filterOptions.map((option) => {
          const Icon = option.icon;
          const isActive = activeFilter === option.id;
          const count = counts[option.id];
          
          return (
            <motion.div
              key={option.id}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Button
                onClick={() => onFilterChange(option.id)}
                variant={isActive ? "default" : "outline"}
                className={`
                  relative h-auto py-4 px-6 rounded-2xl transition-all duration-300
                  ${isActive 
                    ? "bg-primary text-white shadow-lg shadow-primary/30" 
                    : "bg-card/50 hover:bg-card border-border/50 hover:border-primary/50"
                  }
                `}
              >
                <div className="flex flex-col items-center gap-2">
                  <Icon className={`w-6 h-6 ${isActive ? "text-white" : option.color}`} />
                  <span className="text-sm font-medium">{option.name}</span>
                  {count > 0 && (
                    <span className={`
                      text-xs px-2 py-0.5 rounded-full
                      ${isActive 
                        ? "bg-white/20 text-white" 
                        : "bg-primary/10 text-primary"
                      }
                    `}>
                      {count}
                    </span>
                  )}
                </div>
              </Button>
            </motion.div>
          );
        })}
      </div>

      {/* Mobile/Tablet Filters - Scrollable */}
      <div className="lg:hidden overflow-x-auto pb-2 -mx-4 px-4">
        <div className="flex gap-3 min-w-max">
          {filterOptions.map((option) => {
            const Icon = option.icon;
            const isActive = activeFilter === option.id;
            const count = counts[option.id];
            
            return (
              <motion.div
                key={option.id}
                whileTap={{ scale: 0.95 }}
              >
                <Button
                  onClick={() => onFilterChange(option.id)}
                  variant={isActive ? "default" : "outline"}
                  size="sm"
                  className={`
                    relative h-auto py-3 px-4 rounded-xl transition-all duration-300 whitespace-nowrap
                    ${isActive 
                      ? "bg-primary text-white shadow-lg shadow-primary/30" 
                      : "bg-card/50 hover:bg-card border-border/50"
                    }
                  `}
                >
                  <div className="flex items-center gap-2">
                    <Icon className={`w-4 h-4 ${isActive ? "text-white" : option.color}`} />
                    <span className="text-xs sm:text-sm font-medium">{option.name}</span>
                    {count > 0 && (
                      <span className={`
                        text-xs px-1.5 py-0.5 rounded-full
                        ${isActive 
                          ? "bg-white/20 text-white" 
                          : "bg-primary/10 text-primary"
                        }
                      `}>
                        {count}
                      </span>
                    )}
                  </div>
                </Button>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
