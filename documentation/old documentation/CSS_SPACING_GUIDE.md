# CSS Spacing System Guide

## Overview
El sistema de espacios CSS ha sido estandarizado para garantizar consistencia visual en toda la aplicación. Usa una escala de 8 niveles accesibles via variables CSS y clases de utilidad.

## Spacing Scale

```
xs:  4px   (0.25rem)   → Micro spacing, muy pequeño
sm:  8px   (0.5rem)    → Pequeño
md: 16px   (1rem)      → Mediano (DEFAULT)
lg: 24px   (1.5rem)    → Largo
xl: 32px   (2rem)      → Extra largo
2xl: 40px  (2.5rem)    → Doble extra
3xl: 48px  (3rem)      → Triple extra
```

## CSS Variables (En `/app/static/style.css`)

```css
/* Puedes usar en CSS personalizado */
.custom-box {
  padding: var(--spacing-md);      /* 16px */
  margin: var(--spacing-lg);       /* 24px */
  gap: var(--spacing-sm);          /* 8px */
}
```

## Utility Classes

### Padding (p-*, px-*, py-*)
```html
<!-- Padding universal -->
<div class="p-xs">xs padding (4px)</div>
<div class="p-md">md padding (16px)</div>    <!-- Recomendado -->
<div class="p-lg">lg padding (24px)</div>

<!-- Padding horizontal (left + right) -->
<div class="px-md">16px left + right</div>

<!-- Padding vertical (top + bottom) -->
<div class="py-lg">24px top + bottom</div>
```

### Margin (m-*, mx-*, my-*)
```html
<!-- Margin universal -->
<div class="m-md">16px outer space</div>

<!-- Margin horizontal -->
<div class="mx-auto">Center with auto horizontal margin</div>

<!-- Margin vertical -->
<div class="my-lg">24px top + bottom margin</div>
```

### Gap (gap-*)
Para flexbox/grid containers:
```html
<div class="flex gap-md">
  <button>Button</button>
  <button>Button</button>  <!-- 16px between items -->
</div>

<div class="grid gap-lg">
  <div>Item</div>
  <div>Item</div>  <!-- 24px between items -->
</div>
```

### Space-Y (space-y-*)
Para spacing vertical entre elementos hermanos:
```html
<div class="space-y-md">
  <h1>Title</h1>        <!-- 16px below -->
  <p>Paragraph</p>      <!-- 16px below -->
  <p>Paragraph</p>      <!-- 16px below -->
  <button>Button</button>
</div>
```

## Usage Examples

### Card/Modal Box
```html
<div class="p-lg bg-white rounded-lg shadow-md">
  <h2 class="mb-md">Title</h2>
  <div class="space-y-md">
    <p>Content line 1</p>
    <p>Content line 2</p>
  </div>
  <div class="flex gap-md mt-lg">
    <button class="px-md py-sm">Cancel</button>
    <button class="px-md py-sm">Save</button>
  </div>
</div>
```

### Form Group
```html
<div class="space-y-lg">
  <div class="space-y-xs">
    <label class="block text-sm font-bold">Email</label>
    <input class="w-full px-md py-sm border rounded" type="email">
  </div>
  <div class="space-y-xs">
    <label class="block text-sm font-bold">Password</label>
    <input class="w-full px-md py-sm border rounded" type="password">
  </div>
  <button class="w-full py-md mt-lg">Login</button>
</div>
```

### List/Menu
```html
<nav class="space-y-sm">
  <a href="#" class="block px-md py-sm hover:bg-gray-100">Home</a>
  <a href="#" class="block px-md py-sm hover:bg-gray-100">About</a>
  <a href="#" class="block px-md py-sm hover:bg-gray-100">Contact</a>
</nav>
```

### Flex Row with Items
```html
<div class="flex items-center gap-md p-md bg-gray-50 rounded">
  <img src="avatar.jpg" class="w-12 h-12 rounded-full">
  <div class="flex-1 space-y-xs">
    <h3 class="font-bold">Name</h3>
    <p class="text-gray-600">Description</p>
  </div>
  <button class="px-lg py-sm">Action</button>
</div>
```

## Shadow Scale

También se ha estandarizado la escala de sombras:

```css
--shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
--shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
--shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
```

```html
<!-- Cards with shadows -->
<div class="p-md shadow-md rounded">Simple card</div>
<div class="p-md shadow-lg rounded">Important card</div>
<div class="p-md shadow-xl rounded">Featured card</div>
```

## Best Practices

✅ **DO:**
- Usa las variables CSS para espacios (p-md, gap-lg)
- Mantén consistencia: usa niveles iguales para UI similares
- Mezcla p-, m-, gap-* según necesidad
- space-y-* para listas y columnas

❌ **DON'T:**
- ~~Hardcodea números (px, rem, em)~~ → Usa variables en lugar
- ~~Me 24px, pero tú 25px~~ → Mantén consistencia con escala
- ~~Demasiado nesting de space-y~~ → Simplifica con gap cuando sea posible

## Common Patterns

| Use Case | Recommended Classes |
|----------|-------------------|
| Card padding | `p-lg` (24px all sides) |
| Gap between children | `gap-md` (16px) |
| Section separation | `my-xl` (32px) |
| Button padding | `px-md py-sm` (16px / 8px) |
| List items | `space-y-sm` (8px between) |
| Modal title | `mb-lg` (24px bottom) |
| Input field | `px-md py-sm` + border |
| Horizontal buttons | `flex gap-md` |

## Migration Notes

Si encuentras código antiguo con espacios hardcodeados (style="margin: 20px"), considéra actualizarlo:

```html
<!-- Old -->
<div style="margin: 20px; padding: 15px;">Content</div>

<!-- New (usar clases) -->
<div class="m-xl px-lg py-md">Content</div>
```

---

**Last Updated:** 2026-04-05
**CSS File:** `/app/static/style.css` (lines ~50-150 for variables, ~150-400 for utilities)
