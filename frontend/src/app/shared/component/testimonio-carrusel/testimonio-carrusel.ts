import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';

declare var $: any;

@Component({
  selector: 'app-testimonio-carrusel',
  imports: [CommonModule],
  templateUrl: './testimonio-carrusel.html',
  styleUrl: './testimonio-carrusel.css',
})
export class TestimonioCarrusel {
  testimonials = [
    {
      quote:
        'A lo largo de todo este tiempo en lo que mi hijo a asistido a las terapias, he visto un buen desarrollo en Jose Carlos tanto en el colegio como en su vida diaria',
      img: 'img/testimonial-1.jpeg',
      name: 'Liliana Carrion',
      profession: 'Madre de Familia',
    },
    {
      quote:
        'Tras estos 3 meses de terapia he notado que mi hijo se comporta de una forma mas tranquila, mas sociable, todavia tiene algun que otro problema, pero ha mejorado bastante',
      img: 'img/testimonial-2.jpeg',
      name: 'Claudia Martinez',
      profession: 'Madre de Familia',
    },
    {
      quote:
        'Mi hija a aumentando bastante su vocabulario, utilizando palabras que antes no decia, solo haciendo reciaones de dos silabas, aumentando su capacidad en este aspecto.',
      img: 'img/testimonial-1.jpeg',
      name: 'Liliana Carrion',
      profession: 'Madre de familia',
    },

  ];


   ngOnInit() {
    $(document).ready(function () {
      $('.owl-carousel').owlCarousel({
        loop: true,
        margin: 10,
        nav: true,
        autoplay: true,
        autoplayTimeout: 3000,
        items: 1,
        responsive: {
          0: {
            items: 1,
          },
          600: {
            items: 1,
          },
          1000: {
            items: 1,
          },
        },
      });
    });
  }
}
