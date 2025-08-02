import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RegistroSolicitante } from "../register/registro-solicitante/registro-solicitante";
import { TestimonioCarrusel } from "../../shared/component/testimonio-carrusel/testimonio-carrusel";

type TerapiaId = 'lectoEscritura' | 'conductal' | 'lenguaje' | 'ocupacional' | 'aprendizaje' | 'autismo' | 'down' | 'intelectual';

declare var $: any;

@Component({
  selector: 'app-home',
  imports: [CommonModule, RegistroSolicitante, TestimonioCarrusel],
  templateUrl: './home.html',
  styleUrls: ['./home.css'],
})
export class Home {
  selectedTerapia: { title: string; image: string; description: string } | null = null;
  isModalOpen: boolean = false;

  terapiasInfo: Record<TerapiaId, { title: string; image: string; description: string }> = {
    lectoEscritura: {
      title: 'LECTO-ESCRITURA',
      image: 'img/LECTOESCRITURA.jpg',
      description:
        'En esta terapia, trabajamos para potenciar las habilidades de lectura y escritura de los niños y adolescentes con dificultades en estas áreas. Utilizamos métodos innovadores y personalizados para ayudarles a superar sus retos y alcanzar su máximo potencial.',
    },
    conductal: {
      title: 'CONDUCTUAL',
      image: 'img/CONDUCTUAL.jpg',
      description:
        'En el Centro de Terapias Juan Pablo II, ofrecemos terapia de conducta integral para tratar problemas como agresividad y falta de atención. Nuestro enfoque se basa en técnicas probadas que ayudan a los niños a desarrollar habilidades sociales y emocionales, mejorando su comportamiento y bienestar general.',
    },
    lenguaje: {
      title: 'DE LENGUAJE',
      image: '/img/DE LENGUAJE.jpg',
      description:
        'Es un proceso que se enfoca en ayudar a aquellas personas que enfrentan dificultades para hablar y comunicarse de manera efectiva. En el Centro de Terapias Juan Pablo II, ofrecemos terapia de lenguaje integral para abordar problemas como la disartria, la afasia y otros trastornos del habla.',
    },
    ocupacional: {
      title: 'OCUPACIONAL',
      image: '/img/OCUPACIONAL.jpg',
      description:
        'La terapia ocupacional se enfoca en ayudar a las personas a superar dificultades en actividades cotidianas y mejorar su calidad de vida. En el Centro de Terapias Juan Pablo II, ofrecemos terapia ocupacional integral para abordar problemas como la coordinación motora, la planificación motora y la integración sensorial.',
    },
    aprendizaje: {
      title: 'DE APRENDIZAJE',
      image: '/img/DE APRENDIZAJE.jpg',
      description: 'Enfocada en el aprendizaje y el desarrollo integral de los niños y adolescentes. En el Centro de Terapias Juan Pablo II, ofrecemos terapia de aprendizaje personalizada para ayudar a los niños a superar sus dificultades académicas y potenciar su rendimiento escolar.',
    },
    autismo: {
      title: 'AUTISMO',
      image: '/img/AUTISTA.jpg',
      description:
        'En el Centro de Terapias Juan Pablo II, ofrecemos apoyo especializado para personas con Trastorno del Espectro Autista (TEA). Nuestro enfoque integral incluye terapia conductual, terapia ocupacional y terapia de lenguaje, adaptadas a las necesidades individuales de cada persona con TEA. Trabajamos para mejorar sus habilidades sociales, comunicativas y de aprendizaje, fomentando su desarrollo integral y bienestar emocional.',
    },
    down: {
      title: 'SÍNDROME DE DOWN',
      image: '/img/SINDROME DE DOWN.jpg',
      description:
        'En el Centro de Terapias Juan Pablo II, ofrecemos apoyo especializado para personas con Síndrome de Down (SD). Nuestro enfoque integral incluye terapia conductual, terapia ocupacional y terapia de lenguaje, adaptadas a las necesidades individuales de cada persona con SD. Trabajamos para mejorar sus habilidades sociales, comunicativas y de aprendizaje, fomentando su desarrollo integral y bienestar emocional.',
    },
    intelectual: {
      title: 'DISCAPACIDAD INTELECTUAL',
      image: 'img/DISCAPACIDAD INTELECTUAL.jpg',
      description:
        'En el Centro de Terapias Juan Pablo II, ofrecemos apoyo especializado para personas con Discapacidad Intelectual (DI). Nuestro enfoque integral incluye terapia conductual, terapia ocupacional y terapia de lenguaje, adaptadas a las necesidades individuales de cada persona con DI. Trabajamos para mejorar sus habilidades sociales, comunicativas y de aprendizaje, fomentando su desarrollo integral y bienestar emocional.',
    },
  };

  openModal(terapiaKey: TerapiaId) {
    this.selectedTerapia = this.terapiasInfo[terapiaKey];
    this.isModalOpen = true;
    document.body.classList.add('modal-open');
    setTimeout(() => {
      const modal = document.querySelector('.modal-content-custom') as HTMLElement;
      if (modal) modal.focus();
    }, 0);
  }

  closeModal() {
    this.isModalOpen = false;
    document.body.classList.remove('modal-open');
  }

  scrollToSection() {
    const section = document.getElementById('terapias');
    if (section) {
      section.scrollIntoView({ behavior: 'smooth' });
    }
  }
}
