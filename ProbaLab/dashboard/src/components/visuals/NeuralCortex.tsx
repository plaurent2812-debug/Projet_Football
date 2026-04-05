import { useEffect, useRef } from "react"

/**
 * NeuralCortex — Animated neural network with electric synaptic pulses.
 *
 * Nodes connected by synapses. Electric impulses travel along connections,
 * nodes fire and glow when hit. Organic, brain-like movement.
 * Ultra-tech feel — like watching an AI think in real-time.
 */

interface Props {
    className?: string
    nodeCount?: number
    pulseSpeed?: number  // pixels per frame
}

interface Node {
    x: number
    y: number
    baseX: number
    baseY: number
    r: number
    energy: number      // current glow intensity 0-1
    phase: number       // for organic drift
    connections: number[]
}

interface Pulse {
    from: number
    to: number
    progress: number    // 0-1
    speed: number
    width: number
}

export function NeuralCortex({ className = "", nodeCount = 35, pulseSpeed = 0.012 }: Props) {
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const animRef = useRef<number>(0)
    const stateRef = useRef<{ nodes: Node[]; pulses: Pulse[]; w: number; h: number; mouse: { x: number; y: number } }>({
        nodes: [], pulses: [], w: 0, h: 0, mouse: { x: -1000, y: -1000 }
    })

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext("2d")
        if (!ctx) return

        const dpr = Math.min(window.devicePixelRatio || 1, 2)

        function resize() {
            const rect = canvas!.parentElement?.getBoundingClientRect()
            if (!rect) return
            const s = stateRef.current
            s.w = rect.width
            s.h = rect.height
            canvas!.width = s.w * dpr
            canvas!.height = s.h * dpr
            canvas!.style.width = `${s.w}px`
            canvas!.style.height = `${s.h}px`
            ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
            initNodes()
        }

        function initNodes() {
            const s = stateRef.current
            const nodes: Node[] = []

            for (let i = 0; i < nodeCount; i++) {
                const x = Math.random() * s.w
                const y = Math.random() * s.h
                nodes.push({
                    x, y, baseX: x, baseY: y,
                    r: 0.6 + Math.random() * 0.8,
                    energy: 0,
                    phase: Math.random() * Math.PI * 2,
                    connections: [],
                })
            }

            // Build connections — each node connects to 2-4 nearest neighbors
            const MAX_DIST = Math.min(s.w, s.h) * 0.25
            for (let i = 0; i < nodes.length; i++) {
                const dists: Array<[number, number]> = []
                for (let j = 0; j < nodes.length; j++) {
                    if (i === j) continue
                    const dx = nodes[i].baseX - nodes[j].baseX
                    const dy = nodes[i].baseY - nodes[j].baseY
                    const d = Math.sqrt(dx * dx + dy * dy)
                    if (d < MAX_DIST) dists.push([j, d])
                }
                dists.sort((a, b) => a[1] - b[1])
                const count = 2 + Math.floor(Math.random() * 3) // 2-4 connections
                nodes[i].connections = dists.slice(0, count).map(d => d[0])
            }

            s.nodes = nodes
            s.pulses = []
        }

        function spawnPulse() {
            const s = stateRef.current
            if (s.nodes.length === 0) return

            // Pick a random node with connections
            const startIdx = Math.floor(Math.random() * s.nodes.length)
            const node = s.nodes[startIdx]
            if (node.connections.length === 0) return

            const targetIdx = node.connections[Math.floor(Math.random() * node.connections.length)]

            s.pulses.push({
                from: startIdx,
                to: targetIdx,
                progress: 0,
                speed: pulseSpeed * (0.7 + Math.random() * 0.6),
                width: 0.5 + Math.random() * 0.7,
            })

            // Fire the source node
            node.energy = Math.min(node.energy + 0.5, 1)
        }

        let lastSpawn = 0
        let t = 0

        function draw(now: number) {
            const s = stateRef.current
            t = now * 0.001

            ctx!.clearRect(0, 0, s.w, s.h)

            // Spawn new pulses periodically
            if (now - lastSpawn > 120) { // every ~120ms
                spawnPulse()
                lastSpawn = now
            }

            // Organic node drift
            for (const node of s.nodes) {
                node.x = node.baseX + Math.sin(t * 0.5 + node.phase) * 3
                node.y = node.baseY + Math.cos(t * 0.4 + node.phase * 1.3) * 3
            }

            // Draw connections (dim base lines)
            for (let i = 0; i < s.nodes.length; i++) {
                const node = s.nodes[i]
                for (const j of node.connections) {
                    if (j <= i) continue // draw once
                    const target = s.nodes[j]

                    const maxEnergy = Math.max(node.energy, target.energy)
                    const alpha = 0.03 + maxEnergy * 0.08

                    ctx!.beginPath()
                    ctx!.moveTo(node.x, node.y)
                    ctx!.lineTo(target.x, target.y)
                    ctx!.strokeStyle = `rgba(16, 185, 129, ${alpha})`
                    ctx!.lineWidth = 0.15 + maxEnergy * 0.2
                    ctx!.stroke()
                }
            }

            // Draw & update pulses
            for (let p = s.pulses.length - 1; p >= 0; p--) {
                const pulse = s.pulses[p]
                pulse.progress += pulse.speed

                if (pulse.progress >= 1) {
                    // Pulse arrived — fire target node and maybe chain
                    const targetNode = s.nodes[pulse.to]
                    targetNode.energy = Math.min(targetNode.energy + 0.6, 1)

                    // 40% chance to chain to next node
                    if (Math.random() < 0.4 && targetNode.connections.length > 0) {
                        const nextIdx = targetNode.connections[
                            Math.floor(Math.random() * targetNode.connections.length)
                        ]
                        if (nextIdx !== pulse.from) {
                            s.pulses.push({
                                from: pulse.to,
                                to: nextIdx,
                                progress: 0,
                                speed: pulse.speed * (0.9 + Math.random() * 0.2),
                                width: pulse.width * 0.85,
                            })
                        }
                    }

                    s.pulses.splice(p, 1)
                    continue
                }

                const from = s.nodes[pulse.from]
                const to = s.nodes[pulse.to]
                const px = from.x + (to.x - from.x) * pulse.progress
                const py = from.y + (to.y - from.y) * pulse.progress

                // Pulse glow
                const glowSize = 3 + pulse.width * 4
                const grad = ctx!.createRadialGradient(px, py, 0, px, py, glowSize)
                grad.addColorStop(0, `rgba(52, 211, 153, ${0.5 * pulse.width})`)
                grad.addColorStop(0.5, `rgba(16, 185, 129, ${0.12 * pulse.width})`)
                grad.addColorStop(1, "rgba(16, 185, 129, 0)")
                ctx!.fillStyle = grad
                ctx!.fillRect(px - glowSize, py - glowSize, glowSize * 2, glowSize * 2)

                // Pulse core — tiny bright dot
                ctx!.beginPath()
                ctx!.arc(px, py, pulse.width * 0.8, 0, Math.PI * 2)
                ctx!.fillStyle = `rgba(167, 243, 208, 0.9)`
                ctx!.fill()
            }

            // Mouse proximity — illuminate nearby nodes + draw connections to cursor
            const mx = s.mouse.x
            const my = s.mouse.y
            const MOUSE_RADIUS = 100

            if (mx > 0 && my > 0) {
                for (const node of s.nodes) {
                    const dx = node.x - mx
                    const dy = node.y - my
                    const dist = Math.sqrt(dx * dx + dy * dy)

                    if (dist < MOUSE_RADIUS) {
                        const proximity = 1 - dist / MOUSE_RADIUS
                        // Boost node energy based on proximity
                        node.energy = Math.min(node.energy + proximity * 0.08, 1)

                        // Draw connection line to cursor
                        ctx!.beginPath()
                        ctx!.moveTo(node.x, node.y)
                        ctx!.lineTo(mx, my)
                        ctx!.strokeStyle = `rgba(52, 211, 153, ${proximity * 0.15})`
                        ctx!.lineWidth = proximity * 0.8
                        ctx!.stroke()
                    }
                }

                // Cursor glow
                const cursorGrad = ctx!.createRadialGradient(mx, my, 0, mx, my, 12)
                cursorGrad.addColorStop(0, "rgba(52, 211, 153, 0.1)")
                cursorGrad.addColorStop(1, "rgba(16, 185, 129, 0)")
                ctx!.fillStyle = cursorGrad
                ctx!.fillRect(mx - 12, my - 12, 24, 24)
            }

            // Draw nodes (refined, subtle)
            for (const node of s.nodes) {
                // Node glow when energized
                if (node.energy > 0.1) {
                    const glowR = node.r * 3 + node.energy * 5
                    const grad = ctx!.createRadialGradient(node.x, node.y, 0, node.x, node.y, glowR)
                    grad.addColorStop(0, `rgba(16, 185, 129, ${node.energy * 0.4})`)
                    grad.addColorStop(0.5, `rgba(16, 185, 129, ${node.energy * 0.1})`)
                    grad.addColorStop(1, "rgba(16, 185, 129, 0)")
                    ctx!.fillStyle = grad
                    ctx!.fillRect(node.x - glowR, node.y - glowR, glowR * 2, glowR * 2)
                }

                // Node core
                ctx!.beginPath()
                ctx!.arc(node.x, node.y, node.r, 0, Math.PI * 2)
                const brightness = 0.15 + node.energy * 0.85
                ctx!.fillStyle = `rgba(16, 185, 129, ${brightness})`
                ctx!.fill()

                // Decay energy
                node.energy *= 0.96
            }

            animRef.current = requestAnimationFrame(draw)
        }

        // ── Mouse / touch interaction ──────────────────────────
        function onPointerMove(e: PointerEvent) {
            const rect = canvas!.getBoundingClientRect()
            stateRef.current.mouse.x = e.clientX - rect.left
            stateRef.current.mouse.y = e.clientY - rect.top
        }

        function onPointerLeave() {
            stateRef.current.mouse.x = -1000
            stateRef.current.mouse.y = -1000
        }

        function onPointerDown(e: PointerEvent) {
            const rect = canvas!.getBoundingClientRect()
            const clickX = e.clientX - rect.left
            const clickY = e.clientY - rect.top
            const s = stateRef.current

            // Find closest node and fire a burst of pulses from it
            let closestIdx = 0
            let closestDist = Infinity
            for (let i = 0; i < s.nodes.length; i++) {
                const dx = s.nodes[i].x - clickX
                const dy = s.nodes[i].y - clickY
                const d = dx * dx + dy * dy
                if (d < closestDist) { closestDist = d; closestIdx = i }
            }

            const node = s.nodes[closestIdx]
            node.energy = 1

            // Fire pulses to ALL connections (burst)
            for (const targetIdx of node.connections) {
                s.pulses.push({
                    from: closestIdx,
                    to: targetIdx,
                    progress: 0,
                    speed: pulseSpeed * (1 + Math.random() * 0.5),
                    width: 0.8 + Math.random() * 0.5,
                })
            }
        }

        resize()
        animRef.current = requestAnimationFrame(draw)

        canvas.addEventListener("pointermove", onPointerMove)
        canvas.addEventListener("pointerleave", onPointerLeave)
        canvas.addEventListener("pointerdown", onPointerDown)
        window.addEventListener("resize", () => { resize() })

        return () => {
            cancelAnimationFrame(animRef.current)
            canvas.removeEventListener("pointermove", onPointerMove)
            canvas.removeEventListener("pointerleave", onPointerLeave)
            canvas.removeEventListener("pointerdown", onPointerDown)
            window.removeEventListener("resize", resize)
        }
    }, [nodeCount, pulseSpeed])

    return (
        <canvas
            ref={canvasRef}
            className={`absolute inset-0 ${className}`}
            style={{ touchAction: "none" }}
        />
    )
}
