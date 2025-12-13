import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const inputVariants = cva(
  "flex w-full rounded-lg border px-4 py-2.5 text-sm transition-all duration-200 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground/60 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "border-input bg-background focus-visible:ring-2 focus-visible:ring-primary/20 focus-visible:border-primary",
        glass:
          "glass border-[var(--glass-border)] focus-visible:border-[var(--glass-border-strong)] focus-visible:ring-2 focus-visible:ring-white/20",
        filled:
          "border-transparent bg-muted focus-visible:bg-background focus-visible:ring-2 focus-visible:ring-primary/20 focus-visible:border-input",
        ghost:
          "border-transparent bg-transparent focus-visible:bg-muted/50 focus-visible:border-input",
      },
      inputSize: {
        sm: "h-9 text-xs px-3",
        default: "h-11",
        lg: "h-12 text-base px-5",
      },
    },
    defaultVariants: {
      variant: "default",
      inputSize: "default",
    },
  }
)

export interface InputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size">,
    VariantProps<typeof inputVariants> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, variant, inputSize, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(inputVariants({ variant, inputSize }), className)}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

// eslint-disable-next-line react-refresh/only-export-components
export { Input, inputVariants }
