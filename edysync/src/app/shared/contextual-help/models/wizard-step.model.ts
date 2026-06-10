export interface WizardStep {
  selector: string;
  title: string;
  description: string;
  position?: 'top' | 'bottom' | 'left' | 'right' | 'center';
  highlightPadding?: number;
}

export interface WizardConfig {
  route: string;
  role?: string;
  steps: WizardStep[];
}
