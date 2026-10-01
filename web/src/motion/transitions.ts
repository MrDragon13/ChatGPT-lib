export const heroMotion = {
  initial: { opacity: 0, x: 26, y: 12 },
  enter: { opacity: 1, x: 0, y: 0 },
  exit: { opacity: 0, x: -18, y: 4 },
  transition: { type: "spring" as const, stiffness: 92, damping: 20, mass: 0.9 },
};

export const cardMotion = {
  hover: { y: -6, scale: 1.015 },
  tap: { scale: 0.985 },
  transition: { type: "spring" as const, stiffness: 260, damping: 24, mass: 0.72 },
};

export const revealMotion = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 },
  transition: { type: "spring" as const, stiffness: 110, damping: 22, mass: 0.82 },
};
