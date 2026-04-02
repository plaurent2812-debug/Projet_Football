/**
 * pushSubscription.ts — Web Push subscription management.
 *
 * Handles:
 * 1. Service Worker registration
 * 2. Push permission request
 * 3. PushSubscription creation (VAPID)
 * 4. Sending subscription to backend
 */

const API_BASE = import.meta.env.VITE_API_URL || "" // matches API_ROOT from api.js
// VAPID public key — must be set via VITE_VAPID_PUBLIC_KEY env var
const VAPID_PUBLIC_KEY = import.meta.env.VITE_VAPID_PUBLIC_KEY || ""

/**
 * Convert a URL-safe base64 string to a Uint8Array (for applicationServerKey).
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/")
  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}

/**
 * Check if push notifications are supported in this browser.
 */
export function isPushSupported(): boolean {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window
}

/**
 * Get the current push permission state.
 */
export function getPushPermission(): NotificationPermission {
  if (!("Notification" in window)) return "denied"
  return Notification.permission
}

/**
 * Subscribe to push notifications.
 * 1. Registers the service worker
 * 2. Requests notification permission
 * 3. Creates a PushSubscription
 * 4. Sends it to the backend
 *
 * Returns true on success, false on failure.
 */
export async function subscribeToPush(): Promise<boolean> {
  if (!isPushSupported()) {
    console.warn("Push notifications are not supported in this browser")
    return false
  }

  if (!VAPID_PUBLIC_KEY) {
    console.error("VAPID_PUBLIC_KEY is not configured")
    return false
  }

  try {
    // 1. Register service worker
    const registration = await navigator.serviceWorker.register("/sw.js")
    await navigator.serviceWorker.ready

    // 2. Request permission
    const permission = await Notification.requestPermission()
    if (permission !== "granted") {
      console.warn("Notification permission denied")
      return false
    }

    // 3. Subscribe to push
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
    })

    // 4. Send subscription to backend
    const res = await fetch(`${API_BASE}/api/push/subscribe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(subscription.toJSON()),
    })

    if (!res.ok) {
      console.error("Failed to save push subscription:", await res.text())
      return false
    }

    console.log("✅ Push subscription saved successfully")
    return true
  } catch (err) {
    console.error("Push subscription failed:", err)
    return false
  }
}

/**
 * Unsubscribe from push notifications.
 */
export async function unsubscribeFromPush(): Promise<boolean> {
  try {
    const registration = await navigator.serviceWorker.getRegistration()
    if (!registration) return true

    const subscription = await registration.pushManager.getSubscription()
    if (!subscription) return true

    // Unsubscribe locally
    await subscription.unsubscribe()

    // Remove from backend
    await fetch(`${API_BASE}/api/push/unsubscribe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ endpoint: subscription.endpoint }),
    })

    return true
  } catch (err) {
    console.error("Push unsubscribe failed:", err)
    return false
  }
}

/**
 * Check if the user is currently subscribed to push.
 */
export async function isSubscribedToPush(): Promise<boolean> {
  try {
    const registration = await navigator.serviceWorker.getRegistration()
    if (!registration) return false
    const subscription = await registration.pushManager.getSubscription()
    return !!subscription
  } catch {
    return false
  }
}
