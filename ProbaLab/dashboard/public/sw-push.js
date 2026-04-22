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

function parsePushData(event) {
  if (!event.data) return {};
  try {
    return event.data.json();
  } catch {
    return { body: '' };
  }
}

self.addEventListener('push', function (event) {
  var data = parsePushData(event);
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
