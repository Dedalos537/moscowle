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
        'En esta terapia, trabajamos para potenciar las habilidades de lectura y escritura de los niños...',
    },
    conductal: {
      title: 'CONDUCTUAL',
      image: 'img/CONDUCTUAL.jpg',
      description:
        'En el Centro de Terapias Juan Pablo II, ofrecemos terapia de conducta integral para tratar problemas como agresividad...',
    },
    lenguaje: {
      title: 'DE LENGUAJE',
      image: '/img/DE LENGUAJE.jpg',
      description:
        'Es un proceso que se enfoca en ayudar a aquellas personas que enfrentan dificultades para hablar...',
    },
    ocupacional: {
      title: 'OCUPACIONAL',
      image: '/img/OCUPACIONAL.jpg',
      description:
        'La terapia ocupacional se enfoca en ayudar a las personas a superar dificultades en actividades cotidianas...',
    },
    aprendizaje: {
      title: 'DE APRENDIZAJE',
      image: '/img/DE APRENDIZAJE.jpg',
      description: 'Enfocada en el aprendizaje...',
    },
    autismo: {
      title: 'AUTISMO',
      image: '/img/AUTISTA.jpg',
      description:
        'En el Centro de Terapias Juan Pablo II, ofrecemos apoyo especializado para personas con Trastorno del Espectro Autista...',
    },
    down: {
      title: 'SÍNDROME DE DOWN',
      image: '/img/SINDROME DE DOWN.jpg',
      description:
        'En el Centro de Terapias Juan Pablo II, ofrecemos apoyo especializado para personas con Síndrome de Down...',
    },
    intelectual: {
      title: 'DISCAPACIDAD INTELECTUAL',
      image: 'img/DISCAPACIDAD INTELECTUAL.jpg',
      description:
        'En el Centro de Terapias Juan Pablo II, ofrecemos apoyo especializado para personas con Discapacidad Intelectual...',
    },
  };

  openModal(terapiaId: TerapiaId) {
    this.selectedTerapia = this.terapiasInfo[terapiaId];
    this.isModalOpen = true;
  }

  closeModal() {
    this.isModalOpen = false;
  }

  scrollToSection() {
    const section = document.getElementById('terapias');
    if (section) {
      section.scrollIntoView({ behavior: 'smooth' });
    }
  }
}
