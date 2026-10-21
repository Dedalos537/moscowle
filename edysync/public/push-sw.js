/* Moscowle — avisos con el navegador cerrado (Web Push). Lo registra WebPush (core/services/web-push.ts). */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));

self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch {
    data = { title: 'Moscowle', body: event.data ? event.data.text() : '' };
  }
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      // Con la página abierta y a la vista, el aviso ya sale dentro de la app: no se duplica.
      if (clients.some((c) => c.visibilityState === 'visible' && c.focused)) return undefined;
      return self.registration.showNotification(data.title || 'Moscowle', {
        body: data.body || '',
        icon: 'assets/img/logo-silhouette.png',
        badge: 'assets/img/logo-silhouette.png',
        tag: 'moscowle-' + (data.id || Date.now()),
        renotify: true,
        data: { link: data.link || '' },
      });
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const link = (event.notification.data && event.notification.data.link) || '';
  const target = new URL(link.startsWith('/') ? link.slice(1) : link, self.registration.scope).href;
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      for (const c of clients) {
        if (c.url.startsWith(self.registration.scope) && 'focus' in c) {
          c.navigate(target).catch(() => undefined);
          return c.focus();
        }
      }
      return self.clients.openWindow(target);
    }),
  );
});
