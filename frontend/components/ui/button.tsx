import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-semibold ring-offset-background transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]",
  {
    variants: {
      variant: {
        default:
          "bg-gradient-to-r from-[#4ADE80] via-[#2DD4BF] to-[#4FC8F0] text-[#0E1320] shadow-[0_0_18px_-4px_rgba(74,222,128,0.50)] hover:shadow-[0_0_28px_-4px_rgba(74,222,128,0.65)] hover:brightness-110",
        destructive:
          "bg-destructive text-destructive-foreground hover:brightness-110 shadow-[0_0_18px_-6px_rgba(255,96,112,0.55)]",
        outline:
          "border border-[rgba(74,222,128,0.35)] bg-[rgba(24,29,40,0.6)] text-foreground backdrop-blur-md hover:border-[rgba(74,222,128,0.65)] hover:bg-[rgba(24,29,40,0.8)] hover:shadow-[0_0_18px_-6px_rgba(74,222,128,0.45)]",
        secondary:
          "bg-[rgba(79,200,240,0.10)] text-[#7AD9FF] border border-[rgba(79,200,240,0.30)] hover:bg-[rgba(79,200,240,0.16)] hover:shadow-[0_0_18px_-6px_rgba(79,200,240,0.45)]",
        ghost:
          "text-foreground hover:bg-white/[0.05] hover:text-[#4ADE80]",
        link: "text-[#4ADE80] underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-5 py-2",
        sm: "h-9 rounded-lg px-3.5",
        lg: "h-12 rounded-xl px-8 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
