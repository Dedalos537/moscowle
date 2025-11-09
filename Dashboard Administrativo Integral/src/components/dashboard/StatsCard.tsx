import { LucideIcon } from 'lucide-react';
import { Card } from '../ui/card';
import { cn } from '../ui/utils';

interface StatsCardProps {
  title: string;
  value: string | number;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon: LucideIcon;
  iconBgColor?: string;
  iconColor?: string;
}

export function StatsCard({ 
  title, 
  value, 
  change, 
  changeType = 'neutral', 
  icon: Icon,
  iconBgColor = 'bg-[#E8F5E9] dark:bg-[#2E7D32]/20',
  iconColor = 'text-[#4CAF50]'
}: StatsCardProps) {
  return (
    <Card className="p-6 hover:shadow-lg transition-shadow duration-300 border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{title}</p>
          <h3 className="text-gray-900 dark:text-white mb-2">{value}</h3>
          {change && (
            <p className={cn(
              "text-sm",
              changeType === 'positive' && "text-[#4CAF50]",
              changeType === 'negative' && "text-red-500",
              changeType === 'neutral' && "text-gray-500"
            )}>
              {change}
            </p>
          )}
        </div>
        <div className={cn(
          "w-12 h-12 rounded-xl flex items-center justify-center",
          iconBgColor
        )}>
          <Icon className={cn("w-6 h-6", iconColor)} />
        </div>
      </div>
    </Card>
  );
}
