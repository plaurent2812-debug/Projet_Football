import { useEffect, useRef } from "react"

/**
 * AuroraBackground — Full-section animated aurora/northern lights effect.
 *
 * Multiple layered gradient waves flow across the canvas, creating
 * a mesmerizing premium background reminiscent of Stripe's hero.
 * Uses simplex-like noise for organic movement.
 */

interface Props {
    className?: string
    intensity?: number  // 0-1, controls brightness (default 0.5)
}

export function AuroraBackground({ className = "", intensity = 0.5 }: Props) {
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const animRef = useRef<number>(0)

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext("2d")
        if (!ctx) return

        let w = 0, h = 0
        const dpr = Math.min(window.devicePixelRatio || 1, 2)

        function resize() {
            const rect = canvas!.parentElement?.getBoundingClientRect()
            if (!rect) return
            w = rect.width
            h = rect.height
            canvas!.width = w * dpr
            canvas!.height = h * dpr
            canvas!.style.width = `${w}px`
            canvas!.style.height = `${h}px`
            ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
        }

        // Simple pseudo-noise function (no dependency needed)
        function noise(x: number, y: number, t: number): number {
            const n = Math.sin(x * 0.8 + t) * Math.cos(y * 0.6 + t * 0.7)
                    + Math.sin(x * 0.3 - t * 0.5) * Math.cos(y * 1.2 + t * 0.3)
                    + Math.sin((x + y) * 0.5 + t * 0.8) * 0.5
            return (n + 2) / 4 // normalize to 0-1
        }

        // Aurora wave layers
        const layers = [
            { color: [16, 185, 129], speed: 0.0003, freq: 0.003, amp: 0.7, yOffset: 0.3 },   // emerald
            { color: [6, 182, 212], speed: 0.0004, freq: 0.002, amp: 0.5, yOffset: 0.5 },     // cyan
            { color: [139, 92, 246], speed: 0.0002, freq: 0.004, amp: 0.4, yOffset: 0.6 },    // violet
            { color: [16, 185, 129], speed: 0.0005, freq: 0.005, amp: 0.3, yOffset: 0.4 },    // emerald 2
        ]

        let startTime = performance.now()

        function draw(now: number) {
            const t = (now - startTime)

            // Clear with slight trail (creates glow persistence)
            ctx!.fillStyle = "rgba(0, 0, 0, 0.03)"
            ctx!.fillRect(0, 0, w, h)
            ctx!.clearRect(0, 0, w, h)

            for (const layer of layers) {
                const time = t * layer.speed

                ctx!.beginPath()
                ctx!.moveTo(0, h)

                // Draw wave shape
                const steps = Math.ceil(w / 4)
                for (let i = 0; i <= steps; i++) {
                    const x = (i / steps) * w
                    const n = noise(x * layer.freq, 0, time)
                    const y = h * layer.yOffset + Math.sin(x * layer.freq + time * 3) * h * 0.15 * layer.amp
                        + n * h * 0.1 * layer.amp
                    if (i === 0) ctx!.moveTo(x, y)
                    else ctx!.lineTo(x, y)
                }

                // Close path to bottom
                ctx!.lineTo(w, h)
                ctx!.lineTo(0, h)
                ctx!.closePath()

                // Gradient fill
                const grad = ctx!.createLinearGradient(0, 0, w, h)
                const [r, g, b] = layer.color
                const a = intensity * 0.12 * layer.amp
                grad.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${a * 0.5})`)
                grad.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, ${a})`)
                grad.addColorStop(1, `rgba(${r}, ${g}, ${b}, ${a * 0.3})`)
                ctx!.fillStyle = grad
                ctx!.fill()
            }

            // Add subtle scan line effect
            const scanY = (Math.sin(t * 0.001) * 0.5 + 0.5) * h
            const scanGrad = ctx!.createLinearGradient(0, scanY - 30, 0, scanY + 30)
            scanGrad.addColorStop(0, "rgba(16, 185, 129, 0)")
            scanGrad.addColorStop(0.5, `rgba(16, 185, 129, ${intensity * 0.04})`)
            scanGrad.addColorStop(1, "rgba(16, 185, 129, 0)")
            ctx!.fillStyle = scanGrad
            ctx!.fillRect(0, scanY - 30, w, 60)

            animRef.current = requestAnimationFrame(draw)
        }

        resize()
        animRef.current = requestAnimationFrame(draw)
        window.addEventListener("resize", resize)

        return () => {
            cancelAnimationFrame(animRef.current)
            window.removeEventListener("resize", resize)
        }
    }, [intensity])

    return (
        <canvas
            ref={canvasRef}
            className={`absolute inset-0 pointer-events-none ${className}`}
        />
    )
}
