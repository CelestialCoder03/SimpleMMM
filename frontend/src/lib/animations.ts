/**
 * Framer Motion animation presets for consistent animations across the app.
 */

// Define types inline to avoid import issues with framer-motion versions
type Transition = {
  duration?: number;
  ease?: number[] | string;
  type?: string;
  stiffness?: number;
  damping?: number;
  staggerChildren?: number;
  delayChildren?: number;
  staggerDirection?: number;
  repeat?: number;
};

type Variants = {
  initial?: Record<string, unknown>;
  animate?: Record<string, unknown>;
  exit?: Record<string, unknown>;
  collapsed?: Record<string, unknown>;
  expanded?: Record<string, unknown>;
};

// Timing constants (reduced for professional, snappier feel)
export const DURATION = {
  fast: 0.1,    // Was 0.15
  normal: 0.15, // Was 0.25
  slow: 0.2,    // Was 0.35
} as const;

// Easing curves
export const EASE: Record<string, number[]> = {
  smooth: [0.4, 0, 0.2, 1],
  bounce: [0.34, 1.56, 0.64, 1],
  easeOut: [0, 0, 0.2, 1],
  easeIn: [0.4, 0, 1, 1],
};

// Default transition
export const defaultTransition: Transition = {
  duration: DURATION.normal,
  ease: EASE.smooth,
};

// Fade animations
export const fadeIn: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
};

export const fadeInUp: Variants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
};

export const fadeInDown: Variants = {
  initial: { opacity: 0, y: -20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: 10 },
};

// Scale animations
export const scaleIn: Variants = {
  initial: { opacity: 0, scale: 0.95 },
  animate: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.95 },
};

export const scaleInBounce: Variants = {
  initial: { opacity: 0, scale: 0.9 },
  animate: {
    opacity: 1,
    scale: 1,
    transition: { duration: DURATION.normal, ease: EASE.bounce }
  },
  exit: { opacity: 0, scale: 0.95 },
};

// Slide animations
export const slideInLeft: Variants = {
  initial: { opacity: 0, x: -20 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: 20 },
};

export const slideInRight: Variants = {
  initial: { opacity: 0, x: 20 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -20 },
};

// Page transition
export const pageTransition: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.normal, ease: EASE.smooth }
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: { duration: DURATION.fast, ease: EASE.easeIn }
  },
};

// Stagger container for lists
export const staggerContainer: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1,
    },
  },
  exit: {
    transition: {
      staggerChildren: 0.03,
      staggerDirection: -1,
    },
  },
};

// Stagger item (use with staggerContainer)
export const staggerItem: Variants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
};

// Card animations (subtle, professional - no scale/movement)
export const cardHover = {
  boxShadow: 'var(--shadow-md)',  // Just shadow, no movement
  transition: { duration: DURATION.fast, ease: EASE.smooth },
};

export const cardTap = {
  scale: 0.99,  // Very subtle tap feedback
  transition: { duration: DURATION.fast },
};

// Modal/Dialog animations
export const modalOverlay: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: DURATION.fast } },
  exit: { opacity: 0, transition: { duration: DURATION.fast } },
};

export const modalContent: Variants = {
  initial: { opacity: 0, scale: 0.95, y: 10 },
  animate: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: DURATION.normal, ease: EASE.bounce }
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: 10,
    transition: { duration: DURATION.fast }
  },
};

// Skeleton loading pulse
export const skeletonPulse: Variants = {
  initial: { opacity: 0.5 },
  animate: {
    opacity: [0.5, 1, 0.5],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
};

// Number counter animation helper
export const counterSpring = {
  type: 'spring',
  stiffness: 100,
  damping: 15,
};

// Tooltip animations
export const tooltip: Variants = {
  initial: { opacity: 0, scale: 0.95, y: 5 },
  animate: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: DURATION.fast }
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    transition: { duration: DURATION.fast }
  },
};

// Dropdown animations
export const dropdown: Variants = {
  initial: { opacity: 0, y: -10, scaleY: 0.95 },
  animate: {
    opacity: 1,
    y: 0,
    scaleY: 1,
    transition: { duration: DURATION.fast, ease: EASE.easeOut }
  },
  exit: {
    opacity: 0,
    y: -10,
    scaleY: 0.95,
    transition: { duration: DURATION.fast }
  },
};

// Sidebar animations
export const sidebarExpand: Variants = {
  collapsed: { width: 64 },
  expanded: { width: 256 },
};

// Progress bar animation
export const progressBar = (progress: number) => ({
  initial: { width: 0 },
  animate: {
    width: `${progress}%`,
    transition: { duration: DURATION.slow, ease: EASE.smooth }
  },
});

// ========================================
// Glassmorphism Animation Presets
// ========================================

// Expo easing for smoother, more refined animations
export const EASE_OUT_EXPO = [0.22, 1, 0.36, 1];

// Glass card entrance with scale and blur
export const glassCardIn: Variants = {
  initial: {
    opacity: 0,
    y: 20,
    scale: 0.98,
  },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.4,
      ease: EASE_OUT_EXPO
    }
  },
  exit: {
    opacity: 0,
    y: -10,
    scale: 0.98,
    transition: { duration: DURATION.fast }
  },
};

// Subtle glass card entrance (less dramatic)
export const glassCardInSubtle: Variants = {
  initial: {
    opacity: 0,
    y: 12,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.35,
      ease: EASE_OUT_EXPO
    }
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: { duration: DURATION.fast }
  },
};

// Page transition with blur effect (for route changes)
export const pageTransitionGlass: Variants = {
  initial: {
    opacity: 0,
    y: 16,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: EASE_OUT_EXPO
    }
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: {
      duration: DURATION.fast,
      ease: EASE.easeIn
    }
  },
};

// Hover lift effect for glass cards (reduced movement for professional feel)
export const hoverLift = {
  rest: {
    boxShadow: 'var(--shadow-sm)',
    transition: { duration: DURATION.fast, ease: EASE.smooth }
  },
  hover: {
    boxShadow: 'var(--shadow-md)',
    transition: { duration: DURATION.fast, ease: EASE.smooth }
  }
};

// Subtle hover lift (just shadow change)
export const hoverLiftSubtle = {
  rest: {
    boxShadow: 'none',
    transition: { duration: DURATION.fast, ease: EASE.smooth }
  },
  hover: {
    boxShadow: 'var(--shadow-sm)',
    transition: { duration: DURATION.fast, ease: EASE.smooth }
  }
};

// Button press micro-interaction
export const buttonPress = {
  rest: { scale: 1 },
  hover: {
    scale: 1.02,
    transition: { duration: DURATION.fast, ease: EASE.smooth }
  },
  tap: {
    scale: 0.97,
    transition: { duration: 0.1 }
  }
};

// Gradient button with glow effect
export const gradientButtonGlow = {
  rest: {
    scale: 1,
    boxShadow: '0 0 0 0 rgba(59, 130, 246, 0)'
  },
  hover: {
    scale: 1.02,
    boxShadow: '0 0 30px 0 rgba(59, 130, 246, 0.3)',
    transition: { duration: DURATION.normal, ease: EASE.smooth }
  },
  tap: {
    scale: 0.98,
    transition: { duration: 0.1 }
  }
};

// Refined stagger for lists (slower, more elegant)
export const staggerContainerSlow: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.15,
    },
  },
  exit: {
    transition: {
      staggerChildren: 0.05,
      staggerDirection: -1,
    },
  },
};

// Stagger item for glass cards
export const staggerItemGlass: Variants = {
  initial: { opacity: 0, y: 16, scale: 0.98 },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.35,
      ease: EASE_OUT_EXPO
    }
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: { duration: DURATION.fast }
  },
};

// Modal overlay with blur
export const modalOverlayGlass: Variants = {
  initial: {
    opacity: 0,
  },
  animate: {
    opacity: 1,
    transition: { duration: DURATION.normal }
  },
  exit: {
    opacity: 0,
    transition: { duration: DURATION.fast }
  },
};

// Modal content with glass effect
export const modalContentGlass: Variants = {
  initial: {
    opacity: 0,
    scale: 0.95,
    y: 20,
  },
  animate: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      duration: 0.35,
      ease: EASE_OUT_EXPO
    }
  },
  exit: {
    opacity: 0,
    scale: 0.97,
    y: 10,
    transition: { duration: DURATION.fast }
  },
};

// Sidebar glass animation
export const sidebarGlass: Variants = {
  collapsed: {
    width: 64,
    transition: { duration: DURATION.normal, ease: EASE.smooth }
  },
  expanded: {
    width: 256,
    transition: { duration: DURATION.normal, ease: EASE.smooth }
  },
};

// Metric card number animation (for stats)
export const metricNumber: Variants = {
  initial: { opacity: 0, y: 10 },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: EASE_OUT_EXPO
    }
  },
};

// Shine effect for gradient elements (use with pseudo-element)
export const shineEffect = {
  initial: { x: '-100%' },
  animate: {
    x: '100%',
    transition: {
      duration: 1.5,
      ease: 'linear',
      repeat: Infinity,
      repeatDelay: 3,
    }
  }
};

// Tab indicator slide
export const tabIndicator = {
  layout: true,
  transition: {
    type: 'spring',
    stiffness: 500,
    damping: 35,
  }
};

// Accordion expand/collapse
export const accordionContent: Variants = {
  initial: {
    height: 0,
    opacity: 0
  },
  animate: {
    height: 'auto',
    opacity: 1,
    transition: {
      height: { duration: DURATION.normal, ease: EASE.smooth },
      opacity: { duration: DURATION.fast, delay: 0.1 }
    }
  },
  exit: {
    height: 0,
    opacity: 0,
    transition: {
      height: { duration: DURATION.fast, ease: EASE.smooth },
      opacity: { duration: DURATION.fast }
    }
  },
};

// Notification toast entrance
export const toastIn: Variants = {
  initial: {
    opacity: 0,
    y: -20,
    scale: 0.95,
    x: 20
  },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    x: 0,
    transition: {
      duration: 0.35,
      ease: EASE_OUT_EXPO
    }
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    x: 20,
    transition: { duration: DURATION.fast }
  },
};

// Floating decorative elements (for backgrounds)
export const floatingOrb = {
  animate: {
    y: [0, -20, 0],
    x: [0, 10, 0],
    scale: [1, 1.05, 1],
    transition: {
      duration: 8,
      repeat: Infinity,
      ease: 'easeInOut',
    }
  }
};

// Chart animation (for data visualization entry)
export const chartIn: Variants = {
  initial: {
    opacity: 0,
    scale: 0.98,
  },
  animate: {
    opacity: 1,
    scale: 1,
    transition: {
      duration: 0.5,
      ease: EASE_OUT_EXPO,
      delay: 0.2
    }
  },
};
