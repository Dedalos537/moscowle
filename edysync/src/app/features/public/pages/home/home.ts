import { Component, OnInit, AfterViewInit, OnDestroy, ElementRef, ViewChild } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';

interface Feature {
  icon: string;
  title: string;
  description: string;
}

interface Stat {
  value: number;
  suffix: string;
  label: string;
  icon: string;
}

interface Testimonial {
  avatar: string;
  name: string;
  role: string;
  quote: string;
}

@Component({
  selector: 'app-home',
  standalone: false,
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class Home implements OnInit, AfterViewInit, OnDestroy {
  features: Feature[] = [
    {
      icon: 'psychology',
      title: 'Evaluación Inteligente',
      description: 'Evaluaciones automatizadas con IA que analizan el progreso del paciente y sugieren intervenciones personalizadas en tiempo real.',
    },
    {
      icon: 'heart_plus',
      title: 'Terapia Personalizada',
      description: 'Planes de tratamiento adaptados a las necesidades únicas de cada paciente con herramientas interactivas y seguimiento continuo.',
    },
    {
      icon: 'monitoring',
      title: 'Seguimiento en Tiempo Real',
      description: 'Monitorea el avance de tus pacientes al instante con dashboards dinámicos, métricas clave y alertas inteligentes.',
    },
    {
      icon: 'sports_esports',
      title: 'Juegos Interactivos',
      description: 'Actividades lúdico-terapéuticas diseñadas por especialistas para estimular el desarrollo cognitivo y emocional.',
    },
    {
      icon: 'summarize',
      title: 'Reportes Automatizados',
      description: 'Genera informes detallados del progreso terapéutico con un solo clic, listos para compartir con pacientes y colegas.',
    },
    {
      icon: 'business',
      title: 'Multi-Sede',
      description: 'Gestiona múltiples centros desde una plataforma unificada con control de acceso por rol y datos centralizados.',
    },
  ];

  stats: Stat[] = [
    { value: 150, suffix: '+', label: 'Pacientes Activos', icon: 'people' },
    { value: 20, suffix: '+', label: 'Terapeutas Certificados', icon: 'badge' },
    { value: 5000, suffix: '+', label: 'Sesiones Completadas', icon: 'calendar_month' },
    { value: 95, suffix: '%', label: 'Satisfacción', icon: 'star' },
  ];

  testimonials: Testimonial[] = [
    {
      avatar: 'https://i.pravatar.cc/80?img=1',
      name: 'María García',
      role: 'Terapeuta Ocupacional',
      quote: 'EdySync transformó mi práctica. Ahora puedo dedicar más tiempo a mis pacientes y menos a la administración. Los reportes automatizados me ahorran horas cada semana.',
    },
    {
      avatar: 'https://i.pravatar.cc/80?img=5',
      name: 'Carlos Mendoza',
      role: 'Director de Centro',
      quote: 'La plataforma multi-sede nos permitió unificar todos nuestros centros. La visibilidad en tiempo real del progreso de cada paciente es simplemente extraordinaria.',
    },
    {
      avatar: 'https://i.pravatar.cc/80?img=9',
      name: 'Ana Torres',
      role: 'Psicóloga Clínica',
      quote: 'Los juegos interactivos han sido un antes y un después en la terapia infantil. Mis pacientes me piden más sesiones y los resultados son notablemente mejores.',
    },
  ];

  displayedStats: number[] = [];
  statsAnimated = false;

  @ViewChild('statsSection', { static: true }) statsSection!: ElementRef;

  private observer: IntersectionObserver | null = null;

  constructor(private headerService: HeaderService) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'EdySync',
      subtitle: 'Centro de Terapias',
      icon: ['fas', 'home'],
    });
    this.displayedStats = this.stats.map(() => 0);
  }

  ngAfterViewInit() {
    this.observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !this.statsAnimated) {
          this.statsAnimated = true;
          this.animateStats();
          this.observer?.disconnect();
        }
      },
      { threshold: 0.3 },
    );

    if (this.statsSection) {
      this.observer.observe(this.statsSection.nativeElement);
    }
  }

  formatNumber(num: number): string {
    return num >= 1000 ? `${Math.floor(num / 1000)},${String(num % 1000).padStart(3, '0')}` : String(num);
  }

  private animateStats() {
    this.stats.forEach((stat, index) => {
      const target = stat.value;
      const duration = 2000;
      const steps = 40;
      const increment = target / steps;
      let step = 0;

      const interval = setInterval(() => {
        step++;
        this.displayedStats[index] = Math.min(Math.round(increment * step), target);
        if (step >= steps) {
          this.displayedStats[index] = target;
          clearInterval(interval);
        }
      }, duration / steps);
    });
  }

  ngOnDestroy() {
    this.observer?.disconnect();
  }
}
