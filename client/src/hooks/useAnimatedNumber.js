import { useEffect, useRef, useState } from "react";

export function useAnimatedNumber(targetValue, duration = 500) {
  const [displayValue, setDisplayValue] = useState(Number(targetValue) || 0);
  const previousValue = useRef(Number(targetValue) || 0);

  useEffect(() => {
    const from = previousValue.current;
    const to = Number(targetValue) || 0;
    previousValue.current = to;

    if (from === to) {
      setDisplayValue(to);
      return undefined;
    }

    const start = performance.now();
    let frame = 0;

    const animate = (now) => {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = Math.round(from + (to - from) * eased);
      setDisplayValue(value);
      if (progress < 1) {
        frame = requestAnimationFrame(animate);
      }
    };

    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [duration, targetValue]);

  return displayValue;
}
