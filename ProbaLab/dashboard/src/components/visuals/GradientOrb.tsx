/**
 * GradientOrb — Animated blurred gradient orb (CSS only).
 *
 * Creates a slowly moving, pulsing gradient sphere behind content.
 * Inspired by Stripe/Vercel hero backgrounds. Pure CSS, zero JS overhead.
 */

interface Props {
    className?: string
}

export function GradientOrb({ className = "" }: Props) {
    return (
        <div className={`absolute inset-0 overflow-hidden pointer-events-none ${className}`}>
            {/* Primary orb — large, slow drift */}
            <div
                className="absolute rounded-full opacity-20 blur-[80px] animate-orb-drift"
                style={{
                    width: "40vw",
                    height: "40vw",
                    maxWidth: "500px",
                    maxHeight: "500px",
                    background: "radial-gradient(circle, hsl(160 84% 45%) 0%, hsl(160 84% 30% / 0) 70%)",
                    top: "10%",
                    left: "20%",
                }}
            />
            {/* Secondary orb — smaller, offset, different speed */}
            <div
                className="absolute rounded-full opacity-10 blur-[60px] animate-orb-drift-reverse"
                style={{
                    width: "25vw",
                    height: "25vw",
                    maxWidth: "300px",
                    maxHeight: "300px",
                    background: "radial-gradient(circle, hsl(180 60% 50%) 0%, hsl(180 60% 30% / 0) 70%)",
                    bottom: "15%",
                    right: "15%",
                }}
            />
        </div>
    )
}
