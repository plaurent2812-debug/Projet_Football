import { useEffect, useRef, useState } from "react"

/**
 * AnimatedCounter — Counts up from 0 to target value on mount/scroll.
 *
 * Uses requestAnimationFrame for smooth 60fps counting.
 * Supports decimals, prefix/suffix, and custom duration.
 */

interface Props {
    value: number
    duration?: number     // ms (default 1200)
    decimals?: number     // decimal places (default 0)
    prefix?: string       // e.g. "+" or "$"
    suffix?: string       // e.g. "%" or " wins"
    className?: string
}

export function AnimatedCounter({
    value,
    duration = 1200,
    decimals = 0,
    prefix = "",
    suffix = "",
    className = "",
}: Props) {
    const [display, setDisplay] = useState("0")
    const ref = useRef<HTMLSpanElement>(null)
    const hasAnimated = useRef(false)

    useEffect(() => {
        if (hasAnimated.current) return

        const el = ref.current
        if (!el) return

        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting && !hasAnimated.current) {
                    hasAnimated.current = true
                    animate()
                    observer.disconnect()
                }
            },
            { threshold: 0.3 }
        )

        observer.observe(el)
        return () => observer.disconnect()
    }, [value])

    function animate() {
        const start = performance.now()

        function tick(now: number) {
            const elapsed = now - start
            const progress = Math.min(elapsed / duration, 1)

            // Ease-out cubic
            const eased = 1 - Math.pow(1 - progress, 3)
            const current = eased * value

            setDisplay(current.toFixed(decimals))

            if (progress < 1) {
                requestAnimationFrame(tick)
            } else {
                setDisplay(value.toFixed(decimals))
            }
        }

        requestAnimationFrame(tick)
    }

    return (
        <span ref={ref} className={className}>
            {prefix}{display}{suffix}
        </span>
    )
}
