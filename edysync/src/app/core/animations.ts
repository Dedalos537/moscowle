import {
  trigger, transition, style, animate, query, group,
  stagger, keyframes, state, sequence, animateChild
} from '@angular/animations';

const EASE = 'cubic-bezier(0.16, 1, 0.3, 1)';
const DURATION = '400ms';
const FAST = '250ms';
const SLOW = '600ms';

export const fadeIn = trigger('fadeIn', [
  transition(':enter', [
    style({ opacity: 0 }),
    animate(`${DURATION} ${EASE}`, style({ opacity: 1 }))
  ])
]);

export const fadeInUp = trigger('fadeInUp', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateY(20px)' }),
    animate(`${DURATION} ${EASE}`, style({ opacity: 1, transform: 'translateY(0)' }))
  ])
]);

export const fadeInDown = trigger('fadeInDown', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateY(-20px)' }),
    animate(`${DURATION} ${EASE}`, style({ opacity: 1, transform: 'translateY(0)' }))
  ])
]);

export const fadeInLeft = trigger('fadeInLeft', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateX(-20px)' }),
    animate(`${DURATION} ${EASE}`, style({ opacity: 1, transform: 'translateX(0)' }))
  ])
]);

export const fadeInRight = trigger('fadeInRight', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateX(20px)' }),
    animate(`${DURATION} ${EASE}`, style({ opacity: 1, transform: 'translateX(0)' }))
  ])
]);

export const scaleIn = trigger('scaleIn', [
  transition(':enter', [
    style({ opacity: 0, transform: 'scale(0.95)' }),
    animate(`${DURATION} ${EASE}`, style({ opacity: 1, transform: 'scale(1)' }))
  ])
]);

export const bounceIn = trigger('bounceIn', [
  transition(':enter', [
    style({ opacity: 0, transform: 'scale(0.8)' }),
    animate(`${FAST} ${EASE}`, style({ opacity: 1, transform: 'scale(1.05)' })),
    animate(`${FAST} ${EASE}`, style({ transform: 'scale(1)' }))
  ])
]);

export const slideInRight = trigger('slideInRight', [
  transition(':enter', [
    style({ transform: 'translateX(100%)' }),
    animate(`${DURATION} ${EASE}`, style({ transform: 'translateX(0)' }))
  ])
]);

export const slideInUp = trigger('slideInUp', [
  transition(':enter', [
    style({ transform: 'translateY(100%)' }),
    animate(`${DURATION} ${EASE}`, style({ transform: 'translateY(0)' }))
  ])
]);

export const collapse = trigger('collapse', [
  state('void', style({ height: 0, opacity: 0, overflow: 'hidden' })),
  state('*', style({ height: '*', opacity: 1, overflow: 'hidden' })),
  transition('void <=> *', animate(`${DURATION} ${EASE}`))
]);

export const listStagger = trigger('listStagger', [
  transition('* => *', [
    query(':enter', [
      style({ opacity: 0, transform: 'translateY(12px)' }),
      stagger('60ms', [
        animate(`${DURATION} ${EASE}`, style({ opacity: 1, transform: 'translateY(0)' }))
      ])
    ], { optional: true })
  ])
]);

export const gridStagger = trigger('gridStagger', [
  transition('* => *', [
    query(':enter', [
      style({ opacity: 0, transform: 'translateY(12px) scale(0.97)' }),
      stagger('40ms', [
        animate(`${DURATION} ${EASE}`, style({ opacity: 1, transform: 'translateY(0) scale(1)' }))
      ])
    ], { optional: true })
  ])
]);

export const routeAnimations = trigger('routeAnimations', [
  transition('* <=> *', [
    query(':enter', [
      style({ opacity: 0 })
    ], { optional: true }),
    query(':leave', [
      style({ position: 'absolute', inset: 0 }),
      animate(`180ms ${EASE}`, style({ opacity: 0 }))
    ], { optional: true }),
    query(':enter', [
      animate(`300ms ${EASE}`, style({ opacity: 1 }))
    ], { optional: true }),
  ])
]);

export const cardEnter = trigger('cardEnter', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateY(24px)' }),
    animate(`${SLOW} ${EASE}`, style({ opacity: 1, transform: 'translateY(0)' }))
  ])
]);

export const pulse = trigger('pulse', [
  transition('* => *', [
    animate(`${DURATION} ${EASE}`, keyframes([
      style({ transform: 'scale(1)', offset: 0 }),
      style({ transform: 'scale(1.05)', offset: 0.5 }),
      style({ transform: 'scale(1)', offset: 1 })
    ]))
  ])
]);

export const shimmerBar = trigger('shimmerBar', [
  transition(':enter', [
    style({ width: '0%' }),
    animate(`${DURATION} ${EASE}`, style({ width: '100%' }))
  ])
]);

export const viewSlide = trigger('viewSlide', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateX(30px) scale(0.97)', filter: 'blur(4px)' }),
    animate(`400ms ${EASE}`, style({ opacity: 1, transform: 'translateX(0) scale(1)', filter: 'blur(0px)' }))
  ]),
  transition(':leave', [
    animate(`250ms ${EASE}`, style({ opacity: 0, transform: 'translateX(-30px) scale(0.97)', filter: 'blur(4px)' }))
  ])
]);

export const statsSlide = trigger('statsSlide', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateY(16px) scale(0.95)' }),
    animate(`350ms 100ms ${EASE}`, style({ opacity: 1, transform: 'translateY(0) scale(1)' }))
  ]),
  transition(':leave', [
    animate(`200ms ${EASE}`, style({ opacity: 0, transform: 'translateY(-10px) scale(0.95)' }))
  ])
]);
