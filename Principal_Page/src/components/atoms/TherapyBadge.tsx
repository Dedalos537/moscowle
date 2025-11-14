import { Badge } from "../ui/badge";

interface TherapyBadgeProps {
  children: React.ReactNode;
  variant?: "specialized" | "integral" | "virtual" | "material";
}

const variantColors = {
  specialized: "bg-[var(--hope-green)] text-[var(--primary-foreground)] hover:bg-[var(--hope-green-dark)]",
  integral: "bg-[var(--secondary)] text-[var(--secondary-foreground)] hover:bg-[var(--hope-green)]",
  virtual: "bg-[var(--hope-green-dark)] text-white hover:bg-[var(--hope-green)]",
  material: "bg-[var(--hope-green-pale)] text-[var(--hope-green-dark)] hover:bg-[var(--hope-green-light)]",
};

export function TherapyBadge({ children, variant = "specialized" }: TherapyBadgeProps) {
  return (
    <Badge className={`${variantColors[variant]} rounded-full px-4 py-1 transition-all duration-300`}>
      {children}
    </Badge>
  );
}
