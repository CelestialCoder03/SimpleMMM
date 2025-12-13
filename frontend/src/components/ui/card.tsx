import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const cardVariants = cva(
  "rounded-lg border text-card-foreground transition-shadow duration-150",
  {
    variants: {
      variant: {
        default: "bg-card",
        // Professional variants for data-focused UIs
        subtle: "bg-card/50",
        elevated: "bg-card shadow-md",
        // Existing glass variants (kept for backward compatibility)
        glass: "glass-card",
        "glass-subtle": "glass-sm bg-[var(--glass-bg-light)]",
        gradient: "bg-gradient-to-br from-card to-card/80 border-0",
        "gradient-primary": "bg-gradient-primary text-white border-0",
        "gradient-accent": "bg-gradient-accent text-white border-0",
        outline: "bg-transparent border-2",
        ghost: "bg-transparent border-0",
      },
      elevation: {
        none: "",
        sm: "shadow-sm hover:shadow",
        default: "shadow-sm hover:shadow-md",
        md: "shadow-md hover:shadow-lg",
        lg: "shadow-lg hover:shadow-xl",
        glass: "shadow-glass hover:shadow-glass-lg",
      },
      hover: {
        none: "",
        lift: "hover-lift",
        scale: "hover-scale",
        // Glow effects kept but reduced via CSS variables
        glow: "hover:glow-primary",
        "glow-accent": "hover:glow-accent",
      },
      padding: {
        none: "",
        sm: "[&>*:first-child]:p-4 [&>*:not(:first-child)]:px-4",
        default: "",
        lg: "[&>*:first-child]:p-8 [&>*:not(:first-child)]:px-8",
      },
    },
    compoundVariants: [
      {
        variant: "glass",
        elevation: "default",
        className: "shadow-glass hover:shadow-glass-lg",
      },
      {
        variant: "glass-subtle",
        elevation: "default",
        className: "shadow-glass-sm hover:shadow-glass",
      },
    ],
    defaultVariants: {
      variant: "default",
      elevation: "default",
      hover: "none",
      padding: "default",
    },
  }
)

interface CardProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, elevation, hover, padding, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardVariants({ variant, elevation, hover, padding }), className)}
      {...props}
    />
  )
)
Card.displayName = "Card"

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  />
))
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "font-semibold leading-none tracking-tight text-foreground",
      className
    )}
    {...props}
  />
))
CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-sm text-muted-foreground leading-relaxed", className)}
    {...props}
  />
))
CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
))
CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  />
))
CardFooter.displayName = "CardFooter"

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }
export type { CardProps }
