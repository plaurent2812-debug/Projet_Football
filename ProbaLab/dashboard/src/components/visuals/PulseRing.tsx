/**
 * PulseRing — Animated concentric rings that pulse outward.
 *
 * Creates a radar/scanner effect. Ideal around logos, CTAs, or
 * key metrics. Pure CSS, zero JS.
 */

interface Props {
    size?: number    // px (default 120)
    color?: string   // CSS color (default emerald)
    className?: string
}

export function PulseRing({ size = 120, color = "hsl(160 84% 45%)", className = "" }: Props) {
    return (
        <div
            className={`absolute pointer-events-none ${className}`}
            style={{ width: size, height: size, left: "50%", top: "50%", transform: "translate(-50%, -50%)" }}
        >
            {[0, 1, 2].map(i => (
                <div
                    key={i}
                    className="absolute inset-0 rounded-full border opacity-0"
                    style={{
                        borderColor: color,
                        borderWidth: 1,
                        animation: `pulse-ring 3s ease-out infinite`,
                        animationDelay: `${i * 1}s`,
                    }}
                />
            ))}
        </div>
    )
}
