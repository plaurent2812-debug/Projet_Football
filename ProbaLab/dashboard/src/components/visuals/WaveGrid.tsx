import { useEffect, useRef } from "react"

/**
 * WaveGrid — Undulating dot grid with wave propagation.
 *
 * A uniform grid of tiny dots that ripple like water surface.
 * Waves propagate from random points. Mouse creates ripples.
 * Clean, minimal, ultra-premium (Linear/Stripe aesthetic).
 */

interface Props { className?: string }

export function WaveGrid({ className = "" }: Props) {
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const animRef = useRef<number>(0)
    const mouseRef = useRef({ x: -1000, y: -1000 })
    const ripplesRef = useRef<Array<{ x: number; y: number; time: number; strength: number }>>([])

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext("2d")
        if (!ctx) return

        let w = 0, h = 0
        const dpr = Math.min(window.devicePixelRatio || 1, 2)
        const GAP = 18   // distance between dots
        let cols = 0, rows = 0

        function resize() {
            const rect = canvas!.parentElement?.getBoundingClientRect()
            if (!rect) return
            w = rect.width; h = rect.height
            canvas!.width = w * dpr; canvas!.height = h * dpr
            canvas!.style.width = `${w}px`; canvas!.style.height = `${h}px`
            ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
            cols = Math.ceil(w / GAP) + 1
            rows = Math.ceil(h / GAP) + 1
        }

        function isDark() { return document.documentElement.classList.contains("dark") }

        // Auto-spawn ripples
        let autoRippleTimer = 0

        function draw(now: number) {
            ctx!.clearRect(0, 0, w, h)
            const t = now * 0.001
            const dark = isDark()

            const [r, g, b] = dark ? [16, 185, 129] : [2, 120, 80]
            const [br, bg2, bb] = dark ? [52, 211, 153] : [5, 150, 105]
            const baseAlpha = dark ? 0.12 : 0.2

            // Auto-spawn ripples
            autoRippleTimer--
            if (autoRippleTimer <= 0) {
                ripplesRef.current.push({
                    x: Math.random() * w,
                    y: Math.random() * h,
                    time: t,
                    strength: 0.5 + Math.random() * 0.5,
                })
                autoRippleTimer = 60 + Math.random() * 120
            }

            // Clean old ripples
            ripplesRef.current = ripplesRef.current.filter(rp => t - rp.time < 4)

            const mx = mouseRef.current.x
            const my = mouseRef.current.y

            for (let row = 0; row < rows; row++) {
                for (let col = 0; col < cols; col++) {
                    const baseX = col * GAP
                    const baseY = row * GAP

                    // Base wave
                    let displacement = Math.sin(baseX * 0.02 + t * 0.8) * Math.cos(baseY * 0.025 + t * 0.6) * 3

                    // Ripple waves
                    let rippleEnergy = 0
                    for (const rp of ripplesRef.current) {
                        const dx = baseX - rp.x
                        const dy = baseY - rp.y
                        const dist = Math.sqrt(dx * dx + dy * dy)
                        const age = t - rp.time
                        const waveRadius = age * 80  // expansion speed
                        const ringDist = Math.abs(dist - waveRadius)

                        if (ringDist < 30) {
                            const fade = Math.max(0, 1 - age / 4) * rp.strength
                            const wave = Math.cos(ringDist * 0.3) * fade
                            displacement += wave * 4
                            rippleEnergy += fade * Math.max(0, 1 - ringDist / 30)
                        }
                    }

                    // Mouse proximity lift
                    let mouseEnergy = 0
                    if (mx > 0) {
                        const mdx = baseX - mx
                        const mdy = baseY - my
                        const mdist = Math.sqrt(mdx * mdx + mdy * mdy)
                        if (mdist < 60) {
                            mouseEnergy = (1 - mdist / 60)
                            displacement += mouseEnergy * 5
                        }
                    }

                    const x = baseX
                    const y = baseY + displacement

                    // Size and alpha based on energy
                    const energy = Math.min(rippleEnergy + mouseEnergy, 1)
                    const size = 0.5 + energy * 1.2
                    const alpha = baseAlpha + energy * 0.6

                    // Draw dot
                    if (energy > 0.1) {
                        // Glow for energized dots
                        const grad = ctx!.createRadialGradient(x, y, 0, x, y, size * 5)
                        grad.addColorStop(0, `rgba(${br}, ${bg2}, ${bb}, ${energy * 0.2})`)
                        grad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`)
                        ctx!.fillStyle = grad
                        ctx!.fillRect(x - size * 5, y - size * 5, size * 10, size * 10)
                    }

                    ctx!.beginPath()
                    ctx!.arc(x, y, size, 0, Math.PI * 2)
                    ctx!.fillStyle = energy > 0.3
                        ? `rgba(${br}, ${bg2}, ${bb}, ${alpha})`
                        : `rgba(${r}, ${g}, ${b}, ${alpha})`
                    ctx!.fill()
                }
            }

            animRef.current = requestAnimationFrame(draw)
        }

        function onPointerMove(e: PointerEvent) {
            const rect = canvas!.getBoundingClientRect()
            mouseRef.current.x = e.clientX - rect.left
            mouseRef.current.y = e.clientY - rect.top
        }

        function onPointerLeave() {
            mouseRef.current.x = -1000
            mouseRef.current.y = -1000
        }

        function onPointerDown(e: PointerEvent) {
            const rect = canvas!.getBoundingClientRect()
            ripplesRef.current.push({
                x: e.clientX - rect.left,
                y: e.clientY - rect.top,
                time: performance.now() * 0.001,
                strength: 1,
            })
        }

        resize()
        animRef.current = requestAnimationFrame(draw)
        canvas.addEventListener("pointermove", onPointerMove)
        canvas.addEventListener("pointerleave", onPointerLeave)
        canvas.addEventListener("pointerdown", onPointerDown)
        window.addEventListener("resize", resize)
        return () => {
            cancelAnimationFrame(animRef.current)
            canvas.removeEventListener("pointermove", onPointerMove)
            canvas.removeEventListener("pointerleave", onPointerLeave)
            canvas.removeEventListener("pointerdown", onPointerDown)
            window.removeEventListener("resize", resize)
        }
    }, [])

    return <canvas ref={canvasRef} className={`absolute inset-0 ${className}`} style={{ touchAction: "none" }} />
}
