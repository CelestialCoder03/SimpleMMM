import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        // Professional default - no translate animation
        default:
          "bg-primary text-primary-foreground shadow-sm hover:bg-primary-hover hover:shadow-md",
        // Professional variant with subtle border
        professional:
          "bg-primary text-primary-foreground shadow-sm hover:bg-primary-hover border border-primary/20",
        // Legacy variants (kept for backward compatibility, but reduced motion)
        gradient:
          "bg-gradient-primary text-white shadow-md hover:shadow-lg hover:shadow-primary/20",
        "gradient-accent":
          "bg-gradient-accent text-white shadow-md hover:shadow-lg hover:shadow-purple-500/20",
        destructive:
          "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
        outline:
          "border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground",
        secondary:
          "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
        ghost:
          "hover:bg-accent/50 hover:text-accent-foreground",
        "ghost-glass":
          "glass hover:bg-white/20 dark:hover:bg-white/10",
        link:
          "text-primary underline-offset-4 hover:underline p-0 h-auto",
        // Glow variants (reduced intensity)
        glow:
          "bg-primary text-primary-foreground shadow-md hover:shadow-glow-primary",
        "glow-accent":
          "bg-gradient-accent text-white shadow-md hover:shadow-glow-accent",
      },
      size: {
        default: "h-10 px-5 py-2",
        sm: "h-8 rounded-md px-4 text-xs",
        // Compact size for data-dense UIs
        compact: "h-7 px-2.5 text-xs rounded-md",
        lg: "h-12 rounded-lg px-8 text-base",
        xl: "h-14 rounded-lg px-10 text-lg font-semibold",
        icon: "h-10 w-10",
        "icon-sm": "h-8 w-8 rounded-md",
        "icon-lg": "h-12 w-12 rounded-lg",
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
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

// eslint-disable-next-line react-refresh/only-export-components
export { Button, buttonVariants }
