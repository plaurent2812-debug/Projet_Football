import { useEffect, useRef } from "react"

/**
 * DataMatrix — Matrix-rain style streams of data.
 *
 * Vertical columns of tiny numbers/symbols falling at different speeds.
 * Occasional horizontal scan lines that "read" the data.
 * Numbers are actual betting-related values (odds, percentages).
 * Ultra-tech, cyberpunk feel.
 */

interface Props { className?: string }

interface Column {
    x: number
    speed: number
    chars: Array<{ char: string; y: number; opacity: number; size: number }>
    nextSpawn: number
}

const CHARS = "0123456789.%+@"
const VALUES = ["1.85", "2.10", "+7%", "54%", "1X2", "EV+", "3.40", "+12", "89%", "0.5", "2.5"]

export function DataMatrix({ className = "" }: Props) {
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const animRef = useRef<number>(0)

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext("2d")
        if (!ctx) return

        let w = 0, h = 0
        const dpr = Math.min(window.devicePixelRatio || 1, 2)
        const columns: Column[] = []

        function resize() {
            const rect = canvas!.parentElement?.getBoundingClientRect()
            if (!rect) return
            w = rect.width; h = rect.height
            canvas!.width = w * dpr; canvas!.height = h * dpr
            canvas!.style.width = `${w}px`; canvas!.style.height = `${h}px`
            ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
            initColumns()
        }

        function isDark() { return document.documentElement.classList.contains("dark") }

        function initColumns() {
            columns.length = 0
            const gap = 28
            for (let x = 0; x < w; x += gap) {
                columns.push({
                    x: x + Math.random() * 8,
                    speed: 0.3 + Math.random() * 0.6,
                    chars: [],
                    nextSpawn: Math.random() * 200,
                })
            }
        }

        let frame = 0
        function draw() {
            frame++
            const dark = isDark()
            const bg = dark ? "rgba(11, 15, 30, 0.08)" : "rgba(255, 255, 255, 0.06)"
            ctx!.fillStyle = bg
            ctx!.fillRect(0, 0, w, h)

            const baseColor = dark ? [16, 185, 129] : [2, 100, 70]
            const brightColor = dark ? [167, 243, 208] : [5, 150, 105]
            const [r, g, b] = baseColor
            const [br, bg2, bb] = brightColor

            for (const col of columns) {
                // Spawn new char
                if (frame > col.nextSpawn) {
                    const isValue = Math.random() < 0.15
                    const char = isValue
                        ? VALUES[Math.floor(Math.random() * VALUES.length)]
                        : CHARS[Math.floor(Math.random() * CHARS.length)]
                    col.chars.push({
                        char,
                        y: -10,
                        opacity: 0.6 + Math.random() * 0.4,
                        size: isValue ? 8 : 7,
                    })
                    col.nextSpawn = frame + 8 + Math.random() * 25
                }

                // Update + draw chars
                for (let i = col.chars.length - 1; i >= 0; i--) {
                    const c = col.chars[i]
                    c.y += col.speed
                    c.opacity -= 0.003

                    if (c.y > h || c.opacity <= 0) {
                        col.chars.splice(i, 1)
                        continue
                    }

                    // Head char is brighter
                    const isHead = i === col.chars.length - 1
                    ctx!.font = `${c.size}px 'SF Mono', 'Fira Code', monospace`
                    if (isHead) {
                        ctx!.fillStyle = `rgba(${br}, ${bg2}, ${bb}, ${Math.min(c.opacity + 0.3, 1)})`
                        // Tiny glow
                        ctx!.shadowColor = `rgba(${br}, ${bg2}, ${bb}, 0.5)`
                        ctx!.shadowBlur = 4
                    } else {
                        ctx!.fillStyle = `rgba(${r}, ${g}, ${b}, ${c.opacity * 0.5})`
                        ctx!.shadowBlur = 0
                    }
                    ctx!.fillText(c.char, col.x, c.y)
                    ctx!.shadowBlur = 0
                }
            }

            // Occasional scan line
            if (Math.random() < 0.005) {
                const scanY = Math.random() * h
                const scanGrad = ctx!.createLinearGradient(0, scanY - 1, 0, scanY + 1)
                scanGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0)`)
                scanGrad.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, 0.15)`)
                scanGrad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`)
                ctx!.fillStyle = scanGrad
                ctx!.fillRect(0, scanY - 1, w, 2)
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
