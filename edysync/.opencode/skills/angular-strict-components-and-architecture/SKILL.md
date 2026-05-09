---
name: angular-strict-components-and-architecture
description: CRITICAL. You MUST use this skill whenever creating, modifying, or structuring Angular components, modules, or services. This defines the STRICT FOLDER ARCHITECTURE (Core, Shared, Features) and CLI requirements for the Moscowle IA frontend.
---

# 1. Project Context (Moscowle IA)
You are working on the frontend of "Moscowle IA", a project integrating Artificial Intelligence models (like Llama and Whisper) for clinical and administrative use. The UI must be modern, responsive, and maintainable. All code generated must follow our strict Angular Modular Architecture to ensure seamless integration with the Python backend APIs.

# 2. Strict Folder Architecture & Module Rules
The project follows a strict Domain-Driven Design. You MUST place any new file in its appropriate location according to this tree:

    src/
    └── app/
        ├── core/               # STRICTLY SINGLETON. Loaded ONLY once.
        │   ├── interceptors/   # JWT injection, HTTP error handling.
        │   ├── guards/         # Route guards.
        │   ├── layout/         # Global skeleton.
        │   ├── services/       # Global singletons.
        │   └── core.module.ts  # => IMPORTED ONLY IN app.module.ts.
        │
        ├── shared/             # Reusable UI/Dumb components.
        │   ├── components/     # Buttons, Modals, Spinners, Cards.
        │   ├── directives/     # Custom directives.
        │   ├── pipes/          # Transformers.
        │   └── shared.module.ts# => EXPORTS all above.
        │
        ├── features/           # Business domains.
        │   ├── public/         # Home, landing page, about.
        │   ├── auth/           # Login, Register.
        │   ├── admin/          # Admin Dashboard, AI config.
        │   ├── patient/        # Patient Portal.
        │   ├── therapist/      # Therapist Portal.
        │   ├── ai-assistant/   # AI Chat/Interaction Module.
        │   ├── analytics/      # Reports and statistics.
        │   └── payments/       # Payment gateways, Yape confirmation.
        │
        ├── app-routing.module.ts # Main Routing (MUST USE LAZY LOADING).
        ├── app.component.html    # Contains only router-outlet.
        └── app.module.ts         # Root Module.

Architecture Constraints:
* Lazy Loading: All modules inside features/ MUST be lazy-loaded in app-routing.module.ts.
* Core vs Shared: If a service holds state or makes HTTP calls, it goes to core/services/. If a component is just UI (like a button), it goes to shared/components/.

# 3. Shared Components Library (Reusable UI)
The project has 6 reusable shared components under `shared/components/`. You MUST use these instead of writing raw HTML/Tailwind for common UI patterns. All are registered in `SharedModule` and already imported by all feature modules.

## 3.1 Button (`app-button`)
```html
<app-button label="Guardar" variant="primary" [icon]="['fas', 'check']" (clicked)="onSave()"></app-button>
<app-button variant="secondary" [disabled]="isLoading">Cargando...</app-button>
<app-button variant="danger" label="Eliminar"></app-button>
<app-button variant="ghost" label="Cancelar" type="button"></app-button>
```
| Input       | Type                                               | Default     |
|-------------|----------------------------------------------------|-------------|
| `label`     | `string`                                           | `'Button'`  |
| `variant`   | `'primary' \| 'secondary' \| 'danger' \| 'ghost'` | `'primary'` |
| `icon`      | `IconProp` (FontAwesome)                           | `undefined` |
| `disabled`  | `boolean`                                          | `false`     |
| `type`      | `'button' \| 'submit'`                             | `'button'`  |
| Output: `clicked` | `EventEmitter<Event>`                        |             |
| Content projection: default slot inside button.                              |

## 3.2 Card (`app-card`)
```html
<app-card title="Resumen" subtitle="Enero 2026" [icon]="['fas', 'chart-bar']">
  <p>Contenido del cuerpo</p>
  <div card-header-actions>
    <app-button variant="ghost" label="Editar"></app-button>
  </div>
  <div card-footer>
    <p class="text-sm text-muted">Actualizado hoy</p>
  </div>
</app-card>
```
| Input      | Type                  | Default     |
|------------|-----------------------|-------------|
| `title`    | `string`              | `undefined` |
| `subtitle` | `string`              | `undefined` |
| `icon`     | `IconProp`            | `undefined` |
| No outputs. Content slots: default (body), `[card-header-actions]` (header right), `[card-footer]` (footer). |

## 3.3 Input (`app-input`)
```html
<app-input id="email" label="Correo electrónico" type="email" placeholder="user@example.com"
           [(value)]="email" [error]="emailError" [icon]="['fas', 'envelope']"></app-input>
```
| Input          | Type                  | Default     |
|----------------|-----------------------|-------------|
| `id`           | `string`              | `''`        |
| `label`        | `string`              | `''`        |
| `type`         | `string`              | `'text'`    |
| `placeholder`  | `string`              | `''`        |
| `value`        | `string`              | `''`        |
| `error`        | `string`              | `undefined` |
| `icon`         | `IconProp`            | `undefined` |
| Output: `valueChange` | `EventEmitter<string>` | Two-way bindable with `[(value)]` |

## 3.4 Spinner (`app-spinner`)
```html
<app-spinner size="lg" colorClass="text-primary"></app-spinner>
<app-spinner size="sm" colorClass="text-white"></app-spinner>
```
| Input        | Type                    | Default         |
|--------------|-------------------------|-----------------|
| `size`       | `'sm' \| 'md' \| 'lg'` | `'md'`          |
| `colorClass` | `string`                | `'text-primary'`|

## 3.5 Alert (`app-alert`)
```html
<app-alert type="error" message="Ocurrió un error al guardar"></app-alert>
<app-alert type="success" message="Cambios guardados correctamente"></app-alert>
<app-alert type="warning" message="Esta acción no se puede deshacer"></app-alert>
```
| Input     | Type                                                     | Default |
|-----------|----------------------------------------------------------|---------|
| `type`    | `'success' \| 'error' \| 'warning' \| 'info'`           | `'info'`|
| `message` | `string`                                                 | `''`    |

## 3.6 Modal (`app-modal`)
```html
<app-modal [isOpen]="isModalOpen" title="Editar usuario" (close)="isModalOpen = false">
  <p>Contenido del modal</p>
  <div modal-footer>
    <app-button variant="ghost" label="Cancelar" (clicked)="isModalOpen = false"></app-button>
    <app-button label="Guardar" (clicked)="onSave()"></app-button>
  </div>
</app-modal>
```
| Input    | Type               | Default |
|----------|--------------------|---------|
| `isOpen` | `boolean`          | `false` |
| `title`  | `string`           | `''`    |
| Output: `close` | `EventEmitter<void>` | Fires on backdrop click or X button |
| Content slots: default (body scrollable), `[modal-footer]` (action buttons).  |

**IMPORTANT**: Always prefer these shared components over raw `<button>`, `<input>`, `<div class="card...">`, etc. If you need a new reusable component, create it inside `shared/components/` and register it in `SharedModule`.

# 4. Environment & Proxy Pattern (Local ↔ Production)

The project uses **Angular environment files** + an **`ApiBaseInterceptor`** to automatically switch ALL API URLs between local development and production. No service needs to import `environment` or know about prefixes.

## 4.1 How It Works (Global Interceptor)

`core/interceptors/api-base.interceptor.ts` intercepts EVERY `HttpClient` request and prepends `environment.apiBaseUrl`:

```typescript
intercept(req, next) {
  const base = environment.apiBaseUrl;  // '' en dev, '/moscowle' en prod
  if (base && req.url.startsWith('/')) {
    req = req.clone({ url: base + req.url });
  }
  return next.handle(req);
}
```

- **Dev** (`apiBaseUrl = ''`): no modification. `/api/sessions` stays as-is → proxy → local Flask.
- **Prod build** (`apiBaseUrl = '/moscowle'`): `/api/sessions` → `/moscowle/api/sessions` → Passenger strips prefix → Flask.

## 4.2 Environment Files

| File | Scope | `apiBaseUrl` | `production` |
|------|-------|-------------|--------------|
| `src/environments/environment.ts` | `ng serve` (dev) | `''` | `false` |
| `src/environments/environment.prod.ts` | `ng build --prod` | `'/moscowle'` | `true` |

Swapped automatically by `fileReplacements` in `angular.json`.

## 4.3 Proxy (`proxy.conf.js`)

Only used during `ng serve`. Reads `PROXY_TARGET` env var (defaults to `http://localhost:5000`). Includes BOTH context sets so it works in dev AND prod-test mode:

```js
const common = ['/api', '/admin/api', '/therapist/api', '/uploads'];
const moscowle = common.map(p => '/moscowle' + p);  // same paths with /moscowle

module.exports = [
  {
    context: [...common, ...moscowle],
    target: TARGET,
    ...
  },
];
```

| Env var | Proxies to | Use case |
|---------|------------|----------|
| *(not set)* | `http://localhost:5000` | Local Flask development |
| `https://www.centrojuanpabloii.com` | Production server | Testing against remote |

## 4.4 NPM Scripts

```bash
npm start              # ng serve → proxy → localhost:5000
npm run start:prod     # ng serve -c production → proxy → www.centrojuanpabloii.com
```

## 4.5 How to Write Services (Simpler Than Before)

Services NEVER need to import `environment` or handle prefixes:

```typescript
// ✅ CORRECTO — el interceptor hace el trabajo
return this.http.get('/api/sessions');
return this.http.post('/admin/api/expenses', data);
return this.http.get('/login', { responseType: 'text' });
return this.http.get('/logout', { responseType: 'text' });
```

# 5. Strict Creation Rules (CLI ONLY)
Whenever asked to create a new element, you MUST NEVER write the files manually to disk. You MUST provide or execute the exact Angular CLI command.
* Component: ng generate component features/domain-name/components/name
* Service: ng generate service core/services/name
* Do not guess; rely on the CLI to generate scaffolding and register elements.

# 6. Styling Architecture (SASS + TailwindCSS)
You must strictly adhere to this styling paradigm:
1. No inline styles: Never use style="...".
2. No HTML pollution: Do not write HTML tags with dozens of utility classes.
3. Use the SASS File: All styling MUST be inside the component's .scss file using Tailwind's @apply.

✅ GOOD Pattern Example:

<button class="btn-primary">Submit Data</button>

// component.scss
.btn-primary {
    @apply bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded transition-colors;
}

# 7. Global Styles Isolation
Reusable styles (like global resets or main background colors) must be appended to src/styles.scss, not inside individual components.

# 8. Component Logic Rules
* Always use strong typing in TypeScript. Avoid any.
* Keep .ts files clean. Delegate data fetching and complex logic to Services.