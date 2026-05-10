import * as React from "react"
import { cn } from "@/lib/utils"

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-11 w-full rounded-xl border border-white/[0.10] bg-[rgba(28,34,48,0.7)] px-4 py-2 text-sm text-foreground placeholder:text-muted-foreground/65 backdrop-blur-md transition-all",
          "file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-[#4ADE80]",
          "hover:border-white/[0.15]",
          "focus-visible:outline-none focus-visible:border-[rgba(74,222,128,0.55)] focus-visible:ring-2 focus-visible:ring-[rgba(74,222,128,0.20)] focus-visible:shadow-[0_0_18px_-6px_rgba(74,222,128,0.50)]",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
