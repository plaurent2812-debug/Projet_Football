import { useEffect, useRef } from "react"

/**
 * TopoMesh — 3D wireframe terrain with glowing peaks.
 *
 * A perspective grid of points with height values driven by noise,
 * creating rolling hills. Peaks glow (representing "detected value").
 * Slow rotation gives depth. Premium data-landscape feel.
 */

interface Props { className?: string }

export function TopoMesh({ className = "" }: Props) {
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
            w = rect.width; h = rect.height
            canvas!.width = w * dpr; canvas!.height = h * dpr
            canvas!.style.width = `${w}px`; canvas!.style.height = `${h}px`
            ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
        }

        function isDark() { return document.documentElement.classList.contains("dark") }

        function noise(x: number, y: number, t: number): number {
            return (Math.sin(x * 0.15 + t) * Math.cos(y * 0.12 + t * 0.7)
                  + Math.sin((x + y) * 0.08 + t * 0.5) * 0.5
                  + Math.sin(x * 0.3 - t * 0.3) * Math.cos(y * 0.25 + t * 0.4) * 0.3) / 1.8
        }

        const COLS = 40
        const ROWS = 20
        const PERSPECTIVE = 0.6  // how much rows compress toward top

        function draw(now: number) {
            ctx!.clearRect(0, 0, w, h)
            const t = now * 0.0004
            const dark = isDark()

            const baseColor = dark ? [16, 185, 129] : [2, 120, 80]
            const peakColor = dark ? [52, 211, 153] : [5, 150, 105]
            const [r, g, b] = baseColor
            const [pr, pg, pb] = peakColor

            const cellW = w / (COLS - 1)
            const totalH = h * 0.85
            const startY = h * 0.1

            // Generate height map
            const heights: number[][] = []
            for (let row = 0; row < ROWS; row++) {
                heights[row] = []
                for (let col = 0; col < COLS; col++) {
                    heights[row][col] = noise(col, row, t) * 25
                }
            }

            // Draw from back to front (painter's algorithm)
            for (let row = 0; row < ROWS - 1; row++) {
                const rowFactor = row / (ROWS - 1)
                const nextRowFactor = (row + 1) / (ROWS - 1)

                // Perspective compression
                const yScale = 1 - Math.pow(1 - rowFactor, PERSPECTIVE) * 0.5
                const nextYScale = 1 - Math.pow(1 - nextRowFactor, PERSPECTIVE) * 0.5

                const baseY = startY + rowFactor * totalH * yScale
                const nextBaseY = startY + nextRowFactor * totalH * nextYScale

                const fadeAlpha = 0.15 + rowFactor * 0.6  // back rows dimmer

                for (let col = 0; col < COLS - 1; col++) {
                    const x1 = col * cellW
                    const x2 = (col + 1) * cellW

                    const h1 = heights[row][col]
                    const h2 = heights[row][col + 1]
                    const h3 = heights[row + 1][col]
                    const h4 = heights[row + 1][col + 1]

                    const y1 = baseY - h1
                    const y2 = baseY - h2
                    const y3 = nextBaseY - h3
                    const y4 = nextBaseY - h4

                    // Peak detection — glow bright if height is above threshold
                    const maxH = Math.max(h1, h2, h3, h4)
                    const isPeak = maxH > 15

                    // Horizontal line (current row)
                    ctx!.beginPath()
                    ctx!.moveTo(x1, y1)
                    ctx!.lineTo(x2, y2)
                    if (isPeak) {
                        ctx!.strokeStyle = `rgba(${pr}, ${pg}, ${pb}, ${fadeAlpha * 0.8})`
                        ctx!.lineWidth = 0.8
                    } else {
                        ctx!.strokeStyle = `rgba(${r}, ${g}, ${b}, ${fadeAlpha * 0.3})`
                        ctx!.lineWidth = 0.4
                    }
                    ctx!.stroke()

                    // Vertical line (to next row)
                    ctx!.beginPath()
                    ctx!.moveTo(x1, y1)
                    ctx!.lineTo(x1, y3)
                    ctx!.strokeStyle = `rgba(${r}, ${g}, ${b}, ${fadeAlpha * 0.15})`
                    ctx!.lineWidth = 0.3
                    ctx!.stroke()

                    // Peak glow
                    if (isPeak) {
                        const peakX = (x1 + x2) / 2
                        const peakY = Math.min(y1, y2) - 2
                        const grad = ctx!.createRadialGradient(peakX, peakY, 0, peakX, peakY, 8)
                        grad.addColorStop(0, `rgba(${pr}, ${pg}, ${pb}, ${fadeAlpha * 0.3})`)
                        grad.addColorStop(1, `rgba(${pr}, ${pg}, ${pb}, 0)`)
                        ctx!.fillStyle = grad
                        ctx!.fillRect(peakX - 8, peakY - 8, 16, 16)
                    }
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
