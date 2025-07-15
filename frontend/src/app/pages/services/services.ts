import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { ServiceCard } from '../../shared/component/service-card/service-card';
interface ServiceInfo {
  title: string;
  image: string;
  description: string;
  category: string;
  icon: string;
}

@Component({
  selector: 'app-services',
  imports: [CommonModule, ServiceCard],
  templateUrl: './services.html',
  styleUrl: './services.css',
})
export class Services {
  selectedTerapia: ServiceInfo | null = null;
  isModalOpen = false;

  terapiasInfo: { [key: string]: ServiceInfo } = {
    lectoEscritura: {
      title: 'LECTO-ESCRITURA',
      image:
        'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=400&h=300&fit=crop&crop=center',
      description:
        'En esta terapia, trabajamos para potenciar las habilidades de lectura y escritura de los niños, utilizando métodos innovadores y personalizados que nos permiten alcanzar grandes logros.',
      category: 'Terapias',
      icon: '📚',
    },
    conductual: {
      title: 'CONDUCTUAL',
      image:
        'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=400&h=300&fit=crop&crop=center',
      description:
        'En el Centro de Terapias Juan Pablo II, ofrecemos terapia de conducta integral para tratar problemas como agresividad, impulsividad, ansiedad y depresión. Nuestro enfoque ayuda a mejorar la calidad de vida, comenzando con la modificación de conductas, clave para el bienestar y desarrollo personal de niños, adolescentes y adultos.',
      category: 'Terapias',
      icon: '🧠',
    },
    lenguaje: {
      title: 'DE LENGUAJE',
      image:
        'https://images.unsplash.com/photo-1576267423445-b2e0074d68a4?w=400&h=300&fit=crop&crop=center',
      description:
        'Es un proceso que se enfoca en ayudar a aquellas personas que enfrentan dificultades para hablar y sus consecuencias como entender, leer o escribir. A través de técnicas personalizadas, el Centro de Terapias Juan Pablo II soluciona problemas como la articulación incorrecta, el retraso en el desarrollo del habla, y dificultades en la comprensión y producción del lenguaje.',
      category: 'Terapias',
      icon: '🗣️',
    },
    aprendizaje: {
      title: 'DE APRENDIZAJE',
      image:
        'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=400&h=300&fit=crop&crop=center',
      description:
        'Terapia especializada en superar dificultades de aprendizaje, utilizando técnicas personalizadas para mejorar el rendimiento académico y las habilidades cognitivas de cada paciente.',
      category: 'Terapias',
      icon: '🎓',
    },
    ocupacional: {
      title: 'OCUPACIONAL',
      image:
        'https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=400&h=300&fit=crop&crop=center',
      description:
        'La terapia ocupacional se enfoca en ayudar a las personas a superar dificultades en actividades cotidianas esenciales como la alimentación, la higiene personal, el control de esfínteres, el estudio y la recreación. En el Centro de Terapias Juan Pablo II, ofrecemos intervenciones personalizadas para fomentar la autosuficiencia y mejorar la calidad de vida de cada paciente.',
      category: 'Terapias',
      icon: '🏠',
    },
    autismo: {
      title: 'AUTISMO (TEA)',
      image:
        'https://images.unsplash.com/photo-1587654780291-39c9404d746b?w=400&h=300&fit=crop&crop=center',
      description:
        'En el Centro de Terapias Juan Pablo II, ofrecemos apoyo especializado para personas con Trastorno del Espectro Autista (TEA). Utilizamos técnicas propias para ayudar a mejorar la comunicación, la interacción social y la adaptación al entorno.',
      category: 'Terapias Integrales',
      icon: '🌈',
    },
    tda: {
      title: 'TDA',
      image:
        'https://images.unsplash.com/photo-1606092195730-5d7b9af1efc5?w=400&h=300&fit=crop&crop=center',
      description:
        'Tratamiento especializado para el Trastorno por Déficit de Atención, enfocado en mejorar la concentración, organización y habilidades ejecutivas a través de técnicas terapéuticas personalizadas.',
      category: 'Terapias Integrales',
      icon: '🎯',
    },
    tdah: {
      title: 'TDAH',
      image:
        'https://images.unsplash.com/photo-1551601651-2a8555f1a136?w=400&h=300&fit=crop&crop=center',
      description:
        'Abordaje integral del Trastorno por Déficit de Atención e Hiperactividad, combinando estrategias conductuales y cognitivas para mejorar el autocontrol, la atención y las habilidades sociales.',
      category: 'Terapias Integrales',
      icon: '⚡',
    },
    down: {
      title: 'SÍNDROME DE DOWN',
      image:
        'https://images.unsplash.com/photo-1544027993-37dbfe43562a?w=400&h=300&fit=crop&crop=center',
      description:
        'En el Centro de Terapias Juan Pablo II, ofrecemos apoyo especializado para personas con Síndrome de Down. Utilizamos técnicas propias para mejorar el desarrollo psicomotor, el lenguaje y la autonomía personal.',
      category: 'Terapias Integrales',
      icon: '💙',
    },
    intelectual: {
      title: 'DISCAPACIDAD INTELECTUAL',
      image:
        'https://images.unsplash.com/photo-1609081219090-a6d81d3085bf?w=400&h=300&fit=crop&crop=center',
      description:
        'En el Centro de Terapias Juan Pablo II, ofrecemos apoyo especializado para personas con Discapacidad Intelectual. Utilizamos técnicas propias para fortalecer las habilidades cognitivas, la comunicación y la independencia funcional.',
      category: 'Terapias Integrales',
      icon: '🧩',
    },
    comunicacionOral: {
      title: 'COMUNICACIÓN ORAL',
      image:
        'https://images.unsplash.com/photo-1577563908411-5077b6dc7624?w=400&h=300&fit=crop&crop=center',
      description:
        'Apoyo virtual especializado en el desarrollo de habilidades de comunicación oral, utilizando herramientas digitales innovadoras para mejorar la expresión verbal y la comprensión auditiva.',
      category: 'Apoyo Virtual',
      icon: '💻',
    },
    lectoEscrituraVirtual: {
      title: 'LECTO-ESCRITURA VIRTUAL',
      image:
        'https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=400&h=300&fit=crop&crop=center',
      description:
        'Programa virtual de apoyo en lectoescritura, diseñado para fortalecer las habilidades de lectura y escritura a través de plataformas digitales interactivas.',
      category: 'Apoyo Virtual',
      icon: '📖',
    },
    matematicas: {
      title: 'MATEMÁTICAS',
      image:
        'https://images.unsplash.com/photo-1509228468518-180dd4864904?w=400&h=300&fit=crop&crop=center',
      description:
        'Apoyo virtual en matemáticas que utiliza metodologías digitales para facilitar el aprendizaje de conceptos numéricos y operaciones matemáticas básicas y avanzadas.',
      category: 'Apoyo Virtual',
      icon: '🔢',
    },
    desarrolloCognitivo: {
      title: 'DESARROLLO COGNITIVO',
      image:
        'https://images.unsplash.com/photo-1606092195730-5d7b9af1efc5?w=400&h=300&fit=crop&crop=center',
      description:
        'Programa virtual enfocado en estimular y desarrollar las funciones cognitivas superiores como memoria, atención, percepción y funciones ejecutivas.',
      category: 'Apoyo Virtual',
      icon: '🧠',
    },
  };

  materialConcreto: { [key: string]: ServiceInfo } = {
    comunicacionOralMaterial: {
      title: 'COMUNICACIÓN ORAL',
      image:
        'https://images.unsplash.com/photo-1596464716127-f2a82984de30?w=400&h=300&fit=crop&crop=center',
      description:
        'Material concreto diseñado para estimular y desarrollar las habilidades de comunicación oral a través de juegos, tarjetas y actividades interactivas.',
      category: 'Material Concreto',
      icon: '🎲',
    },
    lectoEscrituraMaterial: {
      title: 'LECTO-ESCRITURA',
      image:
        'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=400&h=300&fit=crop&crop=center',
      description:
        'Recursos tangibles y manipulativos para el aprendizaje de la lectura y escritura, incluyendo letras móviles, libros sensoriales y material didáctico especializado.',
      category: 'Material Concreto',
      icon: '🔤',
    },
    matematicasMaterial: {
      title: 'MATEMÁTICAS',
      image:
        'https://images.unsplash.com/photo-1587620962725-abab7fe55159?w=400&h=300&fit=crop&crop=center',
      description:
        'Material manipulativo para el aprendizaje de conceptos matemáticos, incluyendo ábacos, bloques lógicos, regletas y otros recursos didácticos concretos.',
      category: 'Material Concreto',
      icon: '🧮',
    },
    desarrolloCognitivoMaterial: {
      title: 'DESARROLLO COGNITIVO',
      image:
        'https://images.unsplash.com/photo-1606092195730-5d7b9af1efc5?w=400&h=300&fit=crop&crop=center',
      description:
        'Recursos físicos y tangibles diseñados para estimular el desarrollo cognitivo, incluyendo rompecabezas, juegos de memoria y material sensorial especializado.',
      category: 'Material Concreto',
      icon: '🧩',
    },
  };

  allServices = { ...this.terapiasInfo, ...this.materialConcreto };

  onOpenModal(serviceKey: string) {
    this.selectedTerapia = this.allServices[serviceKey];
    this.isModalOpen = true;
  }

  closeModal() {
    this.isModalOpen = false;
    this.selectedTerapia = null;
  }

  getServicesByCategory(cat: string) {
    return Object.entries(this.allServices).filter(
      ([_, s]) => s.category === cat
    );
  }

  getCategoryColor(cat: string) {
    switch (cat) {
      case 'Terapias':
        return { primary: '#667eea', secondary: '#764ba2' };
      case 'Terapias Integrales':
        return { primary: '#28a745', secondary: '#20c997' };
      case 'Apoyo Virtual':
        return { primary: '#17a2b8', secondary: '#6f42c1' };
      case 'Material Concreto':
        return { primary: '#ffc107', secondary: '#fd7e14' };
      default:
        return { primary: '#667eea', secondary: '#764ba2' };
    }
  }
}
