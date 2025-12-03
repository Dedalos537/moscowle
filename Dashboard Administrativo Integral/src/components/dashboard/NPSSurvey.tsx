import { useState } from 'react';
import { X, Send } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';

interface NPSSurveyProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (score: number, feedback: string) => void;
}

export function NPSSurvey({ isOpen, onClose, onSubmit }: NPSSurveyProps) {
  const [selectedScore, setSelectedScore] = useState<number | null>(null);
  const [hoveredScore, setHoveredScore] = useState<number | null>(null);
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (selectedScore === null) return;
    
    setIsSubmitting(true);
    try {
      onSubmit(selectedScore, feedback);
      // Reset form
      setSelectedScore(null);
      setFeedback('');
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  const getScoreCategory = (score: number) => {
    if (score <= 6) return 'Detractor';
    if (score <= 8) return 'Pasivo';
    return 'Promotor';
  };

  const getCategoryColor = (score: number) => {
    if (score <= 6) return 'bg-red-500';
    if (score <= 8) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getButtonStyles = (score: number) => {
    const isSelected = selectedScore === score;
    const isHovered = hoveredScore !== null && score <= hoveredScore;
    const isPreview = hoveredScore !== null && selectedScore === null;

    // Determine color based on hovered score or selected score
    let bgColor = 'bg-gray-200 dark:bg-gray-700';
    let textColor = 'text-gray-700 dark:text-gray-300';
    let borderColor = 'border-gray-300 dark:border-gray-600';

    if (isSelected || (isPreview && isHovered)) {
      if (hoveredScore !== null && score <= hoveredScore) {
        // Apply color based on the hovered score's category
        if (hoveredScore <= 6) {
          bgColor = 'bg-red-500';
          borderColor = 'border-red-600';
        } else if (hoveredScore <= 8) {
          bgColor = 'bg-yellow-500';
          borderColor = 'border-yellow-600';
        } else {
          bgColor = 'bg-green-500';
          borderColor = 'border-green-600';
        }
        textColor = 'text-white';
      } else if (isSelected) {
        // Apply color based on selected score's category
        if (selectedScore <= 6) {
          bgColor = 'bg-red-500';
          borderColor = 'border-red-600';
        } else if (selectedScore <= 8) {
          bgColor = 'bg-yellow-500';
          borderColor = 'border-yellow-600';
        } else {
          bgColor = 'bg-green-500';
          borderColor = 'border-green-600';
        }
        textColor = 'text-white';
      }
    }

    return `${bgColor} ${textColor} ${borderColor} ${
      isSelected || (isPreview && isHovered) ? 'scale-110' : 'scale-100'
    } transition-all duration-200 hover:scale-110`;
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="w-full max-w-3xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="relative">
          

          {/* Header */}
          <div className="pr-10 mb-6">
            <DialogTitle className="text-xl font-bold text-gray-900 dark:text-white mb-2">
              ¿Qué tan probable es que recomiendes el Centro de Terapias a un colega o amigo?
            </DialogTitle>
            <DialogDescription className="text-sm text-gray-600 dark:text-gray-400">
              Tu opinión es muy importante para nosotros y nos ayuda a mejorar continuamente
            </DialogDescription>
          </div>

          {/* Scale Labels */}
          <div className="flex justify-between text-xs font-medium text-gray-600 dark:text-gray-400 mb-3 px-2">
            <span>Muy improbable</span>
            <span>Muy probable</span>
          </div>

          {/* NPS Horizontal Score Selection */}
          <div className="space-y-6">
            <div className="flex gap-1.5 justify-between overflow-x-auto pb-2">
              {Array.from({ length: 11 }, (_, i) => i).map((score) => (
                <button
                  key={score}
                  onClick={() => setSelectedScore(score)}
                  onMouseEnter={() => setHoveredScore(score)}
                  onMouseLeave={() => setHoveredScore(null)}
                  className={`flex-shrink-0 w-14 h-14 rounded-full font-bold text-base border-2 border-gray-300 dark:border-gray-600 ${getButtonStyles(score)}`}
                >
                  {score}
                </button>
              ))}
            </div>

            {/* Category Indicator */}
            {selectedScore !== null && (
              <div className="text-center">
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">Clasificación:</p>
                <div className={`inline-block px-6 py-2 rounded-full font-semibold text-white text-sm ${getCategoryColor(selectedScore)}`}>
                  {getScoreCategory(selectedScore)}
                </div>
              </div>
            )}

            {/* Feedback Section */}
            <div className="space-y-3 pt-6 border-t border-gray-200 dark:border-gray-700">
              <label htmlFor="feedback" className="text-sm font-semibold text-gray-900 dark:text-white block">
                Comentarios adicionales (opcional)
              </label>
              <Textarea
                id="feedback"
                placeholder="¿Qué podríamos mejorar? ¿Qué te gustó más? Cualquier comentario es valioso..."
                value={feedback}
                onChange={(e) => {
                  if (e.target.value.length <= 500) {
                    setFeedback(e.target.value);
                  }
                }}
                className="min-h-[100px] resize-none border-gray-300 dark:border-gray-600 focus:ring-2 focus:ring-green-500 dark:focus:ring-green-400 focus:border-transparent dark:focus:border-transparent"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 text-right">
                {feedback.length}/500 caracteres
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-6 pt-6 border-t border-gray-200 dark:border-gray-700 justify-center items-center">
              <button
                onClick={onClose}
                className="w-16 h-16 rounded-full flex items-center justify-center border-2 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-semibold text-sm transition-all hover:scale-110 duration-200"
              >
                Cerrar
              </button>
              <button
                onClick={handleSubmit}
                disabled={selectedScore === null || isSubmitting}
                className="w-16 h-16 rounded-full flex items-center justify-center bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:scale-110 duration-200 flex-col"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
