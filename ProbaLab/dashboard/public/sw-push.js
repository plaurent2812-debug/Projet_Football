/**
 * ProbaLab V2 Push Service Worker.
 *
 * Dedicated worker for the V2 notification stack (Lot 5 Bloc E).
 * The legacy `public/sw.js` remains untouched to avoid breaking the
 * Phase 3 expert-pick notification pipeline.
 *
 * Scope: shows a system notification on incoming push, opens the
 * target URL on click.
 */

/* eslint-disable no-restricted-globals, no-undef */

self.addEventListener('push', function (event) {
  var data = {};
  try {
    if (event.data) {
      data = event.data.json();
    }
  } catch (err) {
    // Fallback : keep data empty so we still render a generic notification.
  }

  var title = data.title || 'ProbaLab';
  var options = {
    body: data.body || '',
    icon: '/favicon.svg',
    badge: '/favicon.svg',
    data: data.url || '/',
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  var url = (event.notification && event.notification.data) || '/';
  event.waitUntil(self.clients.openWindow(url));
});
