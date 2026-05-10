import * as React from "react"
import { cn } from "@/lib/utils"

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[80px] w-full rounded-xl border border-white/[0.10] bg-[rgba(28,34,48,0.7)] px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground/65 backdrop-blur-md transition-all leading-relaxed",
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
Textarea.displayName = "Textarea"

export { Textarea }
