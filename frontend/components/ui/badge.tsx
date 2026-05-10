import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-[rgba(74,222,128,0.40)] bg-[rgba(74,222,128,0.14)] text-[#6FF09A]",
        secondary:
          "border-[rgba(79,200,240,0.40)] bg-[rgba(79,200,240,0.14)] text-[#7AD9FF]",
        destructive:
          "border-[rgba(255,96,112,0.40)] bg-[rgba(255,96,112,0.14)] text-[#FF7080]",
        outline:
          "border-white/15 bg-white/[0.03] text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
