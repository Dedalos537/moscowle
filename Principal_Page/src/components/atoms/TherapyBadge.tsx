import { Badge } from "../ui/badge";

interface TherapyBadgeProps {
  children: React.ReactNode;
  variant?: "specialized" | "integral" | "virtual" | "material";
}

const variantColors = {
  specialized: "bg-[#4CAF50] text-white hover:bg-[#2E7D32]",
  integral: "bg-[#8BC34A] text-white hover:bg-[#4CAF50]",
  virtual: "bg-[#2E7D32] text-white hover:bg-[#1B5E20]",
  material: "bg-[#E8F5E9] text-[#2E7D32] hover:bg-[#C8E6C9]",
};

export function TherapyBadge({ children, variant = "specialized" }: TherapyBadgeProps) {
  return (
    <Badge className={`${variantColors[variant]} rounded-full px-4 py-1 transition-all duration-300`}>
      {children}
    </Badge>
  );
}
