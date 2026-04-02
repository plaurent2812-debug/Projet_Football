/**
 * Service Worker for ProbaLab Push Notifications.
 * Handles incoming push events and shows native notifications.
 */

self.addEventListener("push", function (event) {
  let data = { title: "🎯 ProbaLab", body: "Nouveau prono expert !" };

  try {
    if (event.data) {
      data = event.data.json();
    }
  } catch (e) {
    // Fallback to default
  }

  const options = {
    body: data.body || "Nouveau prono disponible",
    icon: "/favicon.svg",
    badge: "/favicon.svg",
    vibrate: [100, 50, 100],
    tag: "expert-pick-" + Date.now(),
    data: {
      url: data.url || "/paris-du-soir",
    },
    actions: [{ action: "open", title: "Voir le prono" }],
  };

  event.waitUntil(self.registration.showNotification(data.title || "🎯 ProbaLab", options));
});

// Handle notification click → open the app
self.addEventListener("notificationclick", function (event) {
  event.notification.close();

  const url = event.notification.data?.url || "/paris-du-soir";

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (clientList) {
      // If the app is already open, focus it
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && "focus" in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      // Otherwise, open a new window
      return clients.openWindow(url);
    })
  );
});
