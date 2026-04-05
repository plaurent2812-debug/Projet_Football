import { useEffect, useRef } from "react"

/**
 * ParticleNetwork — Canvas 2D animated constellation background.
 *
 * Renders interconnected floating particles that drift slowly,
 * forming connections when close enough. Premium fintech/data feel.
 *
 * Props:
 *   color — base color for particles and lines (CSS color string)
 *   particleCount — number of particles (default 40)
 *   className — additional container classes
 */

interface Props {
    color?: string
    particleCount?: number
    className?: string
}

interface Particle {
    x: number
    y: number
    vx: number
    vy: number
    r: number
    opacity: number
}

export function ParticleNetwork({
    color = "16, 185, 129",  // emerald RGB
    particleCount = 40,
    className = "",
}: Props) {
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const animRef = useRef<number>(0)

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return

        const ctx = canvas.getContext("2d")
        if (!ctx) return

        let w = 0
        let h = 0
        const particles: Particle[] = []
        const CONNECTION_DIST = 120
        const MOUSE = { x: -1000, y: -1000 }

        function resize() {
            const rect = canvas!.parentElement?.getBoundingClientRect()
            if (!rect) return
            const dpr = Math.min(window.devicePixelRatio || 1, 2)
            w = rect.width
            h = rect.height
            canvas!.width = w * dpr
            canvas!.height = h * dpr
            canvas!.style.width = `${w}px`
            canvas!.style.height = `${h}px`
            ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
        }

        function initParticles() {
            particles.length = 0
            for (let i = 0; i < particleCount; i++) {
                particles.push({
                    x: Math.random() * w,
                    y: Math.random() * h,
                    vx: (Math.random() - 0.5) * 0.4,
                    vy: (Math.random() - 0.5) * 0.4,
                    r: Math.random() * 1.5 + 0.5,
                    opacity: Math.random() * 0.5 + 0.3,
                })
            }
        }

        function draw() {
            ctx!.clearRect(0, 0, w, h)

            // Update + draw particles
            for (const p of particles) {
                p.x += p.vx
                p.y += p.vy

                // Bounce off edges
                if (p.x < 0 || p.x > w) p.vx *= -1
                if (p.y < 0 || p.y > h) p.vy *= -1

                // Draw particle
                ctx!.beginPath()
                ctx!.arc(p.x, p.y, p.r, 0, Math.PI * 2)
                ctx!.fillStyle = `rgba(${color}, ${p.opacity})`
                ctx!.fill()
            }

            // Draw connections
            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const dx = particles[i].x - particles[j].x
                    const dy = particles[i].y - particles[j].y
                    const dist = Math.sqrt(dx * dx + dy * dy)

                    if (dist < CONNECTION_DIST) {
                        const alpha = (1 - dist / CONNECTION_DIST) * 0.15
                        ctx!.beginPath()
                        ctx!.moveTo(particles[i].x, particles[i].y)
                        ctx!.lineTo(particles[j].x, particles[j].y)
                        ctx!.strokeStyle = `rgba(${color}, ${alpha})`
                        ctx!.lineWidth = 0.5
                        ctx!.stroke()
                    }
                }

                // Mouse attraction
                const mdx = particles[i].x - MOUSE.x
                const mdy = particles[i].y - MOUSE.y
                const mdist = Math.sqrt(mdx * mdx + mdy * mdy)
                if (mdist < 150) {
                    const alpha = (1 - mdist / 150) * 0.25
                    ctx!.beginPath()
                    ctx!.moveTo(particles[i].x, particles[i].y)
                    ctx!.lineTo(MOUSE.x, MOUSE.y)
                    ctx!.strokeStyle = `rgba(${color}, ${alpha})`
                    ctx!.lineWidth = 0.8
                    ctx!.stroke()
                }
            }

            animRef.current = requestAnimationFrame(draw)
        }

        function onMouseMove(e: MouseEvent) {
            const rect = canvas!.getBoundingClientRect()
            MOUSE.x = e.clientX - rect.left
            MOUSE.y = e.clientY - rect.top
        }

        function onMouseLeave() {
            MOUSE.x = -1000
            MOUSE.y = -1000
        }

        resize()
        initParticles()
        draw()

        window.addEventListener("resize", () => { resize(); initParticles() })
        canvas.addEventListener("mousemove", onMouseMove)
        canvas.addEventListener("mouseleave", onMouseLeave)

        return () => {
            cancelAnimationFrame(animRef.current)
            window.removeEventListener("resize", resize)
            canvas.removeEventListener("mousemove", onMouseMove)
            canvas.removeEventListener("mouseleave", onMouseLeave)
        }
    }, [color, particleCount])

    return (
        <canvas
            ref={canvasRef}
            className={`absolute inset-0 pointer-events-auto ${className}`}
            style={{ opacity: 0.6 }}
        />
    )
}
