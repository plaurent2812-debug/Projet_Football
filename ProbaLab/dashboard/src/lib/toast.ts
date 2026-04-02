/**
 * Lightweight global toast system — no context needed.
 * Usage: import { toast } from '@/lib/toast'
 *        toast.error("Message d'erreur")
 */

type ToastType = "error" | "success" | "info"
type Toast = { id: number; message: string; type: ToastType }
type Listener = (toasts: Toast[]) => void

let toasts: Toast[] = []
let nextId = 0
const listeners = new Set<Listener>()

function notify() {
    listeners.forEach(fn => fn([...toasts]))
}

function add(message: string, type: ToastType, duration = 5000) {
    const id = ++nextId
    toasts = [{ id, message, type }, ...toasts].slice(0, 3)
    notify()
    setTimeout(() => dismiss(id), duration)
}

function dismiss(id: number) {
    toasts = toasts.filter(t => t.id !== id)
    notify()
}

export const toast = {
    error: (msg: string) => add(msg, "error", 6000),
    success: (msg: string) => add(msg, "success", 4000),
    info: (msg: string) => add(msg, "info", 4000),
    dismiss,
    subscribe: (fn: Listener) => { listeners.add(fn); return () => listeners.delete(fn) },
    getToasts: () => [...toasts],
}
