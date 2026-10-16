import { Pipe, PipeTransform, inject } from '@angular/core';
import { PeopleService } from '../../core/services/people.service';

/**
 * Nombre de una persona según «Mostrar personas» (Configuración): `{{ p.patient_name | personLabel: p.patient_id }}`.
 * Impuro a propósito: cambia cuando llega el directorio o cuando el usuario cambia la preferencia.
 */
@Pipe({ name: 'personLabel', standalone: true, pure: false })
export class PersonLabelPipe implements PipeTransform {
  private people = inject(PeopleService);

  transform(name: string | null | undefined, id?: number | null, code?: string | null): string {
    return this.people.label({ name, id, code });
  }
}
