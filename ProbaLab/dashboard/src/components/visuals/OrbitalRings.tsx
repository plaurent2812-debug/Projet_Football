import { useEffect, useRef } from "react"

/**
 * OrbitalRings — Concentric orbiting data points.
 *
 * Multiple rings of particles rotating at different speeds.
 * Occasional "flash" connections between orbits.
 * Central core pulses. Particle accelerator / solar system feel.
 */

interface Props { className?: string }

interface Ring {
    radius: number
    particles: Array<{ angle: number; size: number; speed: number; brightness: number }>
    rotationSpeed: number
    opacity: number
}

export function OrbitalRings({ className = "" }: Props) {
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const animRef = useRef<number>(0)

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext("2d")
        if (!ctx) return

        let w = 0, h = 0
        const dpr = Math.min(window.devicePixelRatio || 1, 2)
        const rings: Ring[] = []

        function resize() {
            const rect = canvas!.parentElement?.getBoundingClientRect()
            if (!rect) return
            w = rect.width; h = rect.height
            canvas!.width = w * dpr; canvas!.height = h * dpr
            canvas!.style.width = `${w}px`; canvas!.style.height = `${h}px`
            ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
            initRings()
        }

        function isDark() { return document.documentElement.classList.contains("dark") }

        function initRings() {
            rings.length = 0
            const maxRadius = Math.min(w, h) * 0.42
            const ringCount = 5

            for (let i = 0; i < ringCount; i++) {
                const radius = maxRadius * (0.25 + (i / (ringCount - 1)) * 0.75)
                const particleCount = 6 + i * 3
                const particles = Array.from({ length: particleCount }, () => ({
                    angle: Math.random() * Math.PI * 2,
                    size: 0.5 + Math.random() * 0.8,
                    speed: (0.2 + Math.random() * 0.3) * (i % 2 === 0 ? 1 : -1),
                    brightness: 0.3 + Math.random() * 0.7,
                }))

                rings.push({
                    radius,
                    particles,
                    rotationSpeed: 0.0003 * (ringCount - i),
                    opacity: 0.2 + (i / ringCount) * 0.3,
                })
            }
        }

        let flashTimer = 0

        function draw(now: number) {
            ctx!.clearRect(0, 0, w, h)
            const t = now * 0.001
            const dark = isDark()
            const cx = w / 2
            const cy = h / 2

            const [r, g, b] = dark ? [16, 185, 129] : [2, 120, 80]
            const [br, bg2, bb] = dark ? [52, 211, 153] : [5, 150, 105]
            const [cr, cg, cb] = dark ? [167, 243, 208] : [2, 100, 70]

            // Draw orbit rings (elliptical for perspective)
            for (const ring of rings) {
                ctx!.beginPath()
                ctx!.ellipse(cx, cy, ring.radius, ring.radius * 0.35, 0, 0, Math.PI * 2)
                ctx!.strokeStyle = `rgba(${r}, ${g}, ${b}, ${ring.opacity * 0.15})`
                ctx!.lineWidth = 0.3
                ctx!.stroke()

                // Update and draw particles
                for (const p of ring.particles) {
                    p.angle += ring.rotationSpeed * p.speed

                    const px = cx + Math.cos(p.angle) * ring.radius
                    const py = cy + Math.sin(p.angle) * ring.radius * 0.35

                    // Z-depth: particles "in front" (bottom) are brighter
                    const zFactor = (Math.sin(p.angle) + 1) / 2  // 0=back, 1=front
                    const alpha = p.brightness * (0.3 + zFactor * 0.7)

                    // Glow
                    if (alpha > 0.5) {
                        const grad = ctx!.createRadialGradient(px, py, 0, px, py, p.size * 4)
                        grad.addColorStop(0, `rgba(${br}, ${bg2}, ${bb}, ${alpha * 0.25})`)
                        grad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`)
                        ctx!.fillStyle = grad
                        ctx!.fillRect(px - p.size * 4, py - p.size * 4, p.size * 8, p.size * 8)
                    }

                    // Dot
                    ctx!.beginPath()
                    ctx!.arc(px, py, p.size * (0.6 + zFactor * 0.4), 0, Math.PI * 2)
                    ctx!.fillStyle = `rgba(${br}, ${bg2}, ${bb}, ${alpha})`
                    ctx!.fill()
                }
            }

            // Central core pulse
            const coreSize = 2 + Math.sin(t * 2) * 0.5
            const coreGrad = ctx!.createRadialGradient(cx, cy, 0, cx, cy, coreSize * 6)
            coreGrad.addColorStop(0, `rgba(${cr}, ${cg}, ${cb}, 0.6)`)
            coreGrad.addColorStop(0.3, `rgba(${br}, ${bg2}, ${bb}, 0.15)`)
            coreGrad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`)
            ctx!.fillStyle = coreGrad
            ctx!.fillRect(cx - coreSize * 6, cy - coreSize * 6, coreSize * 12, coreSize * 12)

            ctx!.beginPath()
            ctx!.arc(cx, cy, coreSize, 0, Math.PI * 2)
            ctx!.fillStyle = `rgba(${cr}, ${cg}, ${cb}, 0.8)`
            ctx!.fill()

            // Occasional flash connection between rings
            flashTimer--
            if (flashTimer <= 0 && rings.length >= 2) {
                flashTimer = 40 + Math.random() * 80
                const r1 = rings[Math.floor(Math.random() * rings.length)]
                const r2 = rings[Math.floor(Math.random() * rings.length)]
                if (r1 !== r2 && r1.particles.length && r2.particles.length) {
                    const p1 = r1.particles[Math.floor(Math.random() * r1.particles.length)]
                    const p2 = r2.particles[Math.floor(Math.random() * r2.particles.length)]
                    const x1 = cx + Math.cos(p1.angle) * r1.radius
                    const y1 = cy + Math.sin(p1.angle) * r1.radius * 0.35
                    const x2 = cx + Math.cos(p2.angle) * r2.radius
                    const y2 = cy + Math.sin(p2.angle) * r2.radius * 0.35

                    ctx!.beginPath()
                    ctx!.moveTo(x1, y1)
                    ctx!.lineTo(x2, y2)
                    ctx!.strokeStyle = `rgba(${br}, ${bg2}, ${bb}, 0.2)`
                    ctx!.lineWidth = 0.5
                    ctx!.stroke()
                }
            }

            animRef.current = requestAnimationFrame(draw)
        }

        resize()
        animRef.current = requestAnimationFrame(draw)
        window.addEventListener("resize", resize)
        return () => { cancelAnimationFrame(animRef.current); window.removeEventListener("resize", resize) }
    }, [])

    return <canvas ref={canvasRef} className={`absolute inset-0 pointer-events-none ${className}`} />
}
