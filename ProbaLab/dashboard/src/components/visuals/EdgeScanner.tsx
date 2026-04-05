import { useEffect, useRef } from "react"

/**
 * EdgeScanner — Radar sweep visualization for "detecting market edges".
 *
 * A rotating scan line sweeps across a circular area. When it passes
 * over "detected" points, they light up with a green pulse.
 * Perfectly themed for "Smart Betting Assistant — finds where the market is wrong".
 */

interface Props {
    size?: number      // px diameter (default 200)
    className?: string
    edgePoints?: number  // number of "detected" edges to show (default 5)
}

export function EdgeScanner({ size = 200, className = "", edgePoints = 5 }: Props) {
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const animRef = useRef<number>(0)
    const pointsRef = useRef<Array<{ angle: number; dist: number; pulse: number; maxPulse: number }>>([])

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext("2d")
        if (!ctx) return

        const dpr = Math.min(window.devicePixelRatio || 1, 2)
        canvas.width = size * dpr
        canvas.height = size * dpr
        canvas.style.width = `${size}px`
        canvas.style.height = `${size}px`
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

        const cx = size / 2
        const cy = size / 2
        const radius = size * 0.42

        // Generate random edge points
        pointsRef.current = Array.from({ length: edgePoints }, () => ({
            angle: Math.random() * Math.PI * 2,
            dist: 0.3 + Math.random() * 0.65,
            pulse: 0,
            maxPulse: 0.6 + Math.random() * 0.4,
        }))

        function draw(now: number) {
            ctx!.clearRect(0, 0, size, size)
            const sweepAngle = (now * 0.001) % (Math.PI * 2)

            // Concentric rings (grid)
            for (let i = 1; i <= 3; i++) {
                const r = radius * (i / 3)
                ctx!.beginPath()
                ctx!.arc(cx, cy, r, 0, Math.PI * 2)
                ctx!.strokeStyle = "rgba(16, 185, 129, 0.08)"
                ctx!.lineWidth = 0.5
                ctx!.stroke()
            }

            // Cross hairs
            ctx!.strokeStyle = "rgba(16, 185, 129, 0.06)"
            ctx!.lineWidth = 0.5
            ctx!.beginPath()
            ctx!.moveTo(cx - radius, cy)
            ctx!.lineTo(cx + radius, cy)
            ctx!.moveTo(cx, cy - radius)
            ctx!.lineTo(cx, cy + radius)
            ctx!.stroke()

            // Sweep cone (fading trail)
            const trailAngle = 0.8 // radians of trail
            const sweepGrad = ctx!.createConicGradient(sweepAngle - trailAngle, cx, cy)
            sweepGrad.addColorStop(0, "rgba(16, 185, 129, 0)")
            sweepGrad.addColorStop(trailAngle / (Math.PI * 2), "rgba(16, 185, 129, 0.12)")
            sweepGrad.addColorStop(trailAngle / (Math.PI * 2) + 0.001, "rgba(16, 185, 129, 0)")
            ctx!.beginPath()
            ctx!.moveTo(cx, cy)
            ctx!.arc(cx, cy, radius, sweepAngle - trailAngle, sweepAngle)
            ctx!.closePath()
            ctx!.fillStyle = sweepGrad
            ctx!.fill()

            // Sweep line
            const lx = cx + Math.cos(sweepAngle) * radius
            const ly = cy + Math.sin(sweepAngle) * radius
            ctx!.beginPath()
            ctx!.moveTo(cx, cy)
            ctx!.lineTo(lx, ly)
            ctx!.strokeStyle = "rgba(16, 185, 129, 0.6)"
            ctx!.lineWidth = 1.5
            ctx!.stroke()

            // Edge points
            for (const pt of pointsRef.current) {
                const px = cx + Math.cos(pt.angle) * radius * pt.dist
                const py = cy + Math.sin(pt.angle) * radius * pt.dist

                // Check if sweep just passed this point
                let angleDiff = sweepAngle - pt.angle
                if (angleDiff < 0) angleDiff += Math.PI * 2
                if (angleDiff < 0.15) {
                    pt.pulse = pt.maxPulse
                }

                // Decay pulse
                pt.pulse *= 0.97

                if (pt.pulse > 0.05) {
                    // Glow
                    const glowGrad = ctx!.createRadialGradient(px, py, 0, px, py, 12)
                    glowGrad.addColorStop(0, `rgba(16, 185, 129, ${pt.pulse * 0.6})`)
                    glowGrad.addColorStop(1, "rgba(16, 185, 129, 0)")
                    ctx!.fillStyle = glowGrad
                    ctx!.fillRect(px - 12, py - 12, 24, 24)
                }

                // Dot (always visible, dim)
                ctx!.beginPath()
                ctx!.arc(px, py, 2, 0, Math.PI * 2)
                ctx!.fillStyle = `rgba(16, 185, 129, ${0.2 + pt.pulse * 0.8})`
                ctx!.fill()
            }

            // Center dot
            ctx!.beginPath()
            ctx!.arc(cx, cy, 2.5, 0, Math.PI * 2)
            ctx!.fillStyle = "rgba(16, 185, 129, 0.8)"
            ctx!.fill()

            animRef.current = requestAnimationFrame(draw)
        }

        animRef.current = requestAnimationFrame(draw)

        return () => cancelAnimationFrame(animRef.current)
    }, [size, edgePoints])

    return (
        <canvas
            ref={canvasRef}
            className={`${className}`}
            style={{ width: size, height: size }}
        />
    )
}
