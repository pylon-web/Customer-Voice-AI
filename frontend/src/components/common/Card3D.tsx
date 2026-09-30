import React, { useRef, useState, useCallback } from 'react';

interface Card3DProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  glowOnHover?: 'cyan' | 'red' | 'amber' | 'emerald' | 'none';
  maxTilt?: number;
  scaleOnHover?: number;
  glare?: boolean;
  disableTilt?: boolean;
}

export const Card3D: React.FC<Card3DProps> = ({
  children,
  className = '',
  onClick,
  glowOnHover = 'cyan',
  maxTilt = 8,
  scaleOnHover = 1.02,
  glare = true,
  disableTilt = false,
}) => {
  const cardRef = useRef<HTMLDivElement>(null);
  const [transformStyle, setTransformStyle] = useState<string>('perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)');
  const [glarePosition, setGlarePosition] = useState<{ x: number; y: number; opacity: number }>({
    x: 50,
    y: 50,
    opacity: 0,
  });
  const [isHovered, setIsHovered] = useState<boolean>(false);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (disableTilt) return;
      if (!cardRef.current) return;

      // UX Guardrail: Freeze tilt when hovering over interactive elements (buttons, links, inputs)
      // to prevent buttons from moving away from the user's cursor
      const target = e.target as HTMLElement | null;
      if (target && target.closest('button, a, input, select, textarea, [role="button"]')) {
        setTransformStyle('perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)');
        return;
      }

      const rect = cardRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      // Calculate tilt angles (-maxTilt to +maxTilt)
      const rotateX = -((y - centerY) / centerY) * maxTilt;
      const rotateY = ((x - centerX) / centerX) * maxTilt;

      setTransformStyle(
        `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) scale3d(${scaleOnHover}, ${scaleOnHover}, ${scaleOnHover})`
      );

      if (glare) {
        setGlarePosition({
          x: (x / rect.width) * 100,
          y: (y / rect.height) * 100,
          opacity: 0.14,
        });
      }
    },
    [disableTilt, maxTilt, scaleOnHover, glare]
  );

  const handleMouseEnter = () => {
    setIsHovered(true);
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    setTransformStyle('perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)');
    setGlarePosition((prev) => ({ ...prev, opacity: 0 }));
  };

  const getGlowClass = () => {
    if (!isHovered || glowOnHover === 'none') return '';
    switch (glowOnHover) {
      case 'cyan':
        return 'shadow-[0_12px_36px_-6px_rgba(56,189,248,0.35)] border-sky-400/60';
      case 'red':
        return 'shadow-[0_12px_36px_-6px_rgba(208,48,39,0.45)] border-[#D03027]';
      case 'amber':
        return 'shadow-[0_12px_36px_-6px_rgba(245,158,11,0.35)] border-amber-400/60';
      case 'emerald':
        return 'shadow-[0_12px_36px_-6px_rgba(16,185,129,0.35)] border-emerald-400/60';
      default:
        return '';
    }
  };

  return (
    <div
      style={{ perspective: '1000px' }}
      className="transition-transform duration-200 ease-out"
    >
      <div
        ref={cardRef}
        onClick={onClick}
        onMouseMove={handleMouseMove}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        style={{
          transform: transformStyle,
          transformStyle: 'preserve-3d',
          transition: isHovered
            ? 'transform 0.08s ease-out, box-shadow 0.25s ease-out, border-color 0.25s ease-out'
            : 'transform 0.4s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.4s ease-out, border-color 0.4s ease-out',
        }}
        className={`relative will-change-transform ${getGlowClass()} ${className}`}
      >
        {/* Dynamic Specular Glare Overlay */}
        {glare && (
          <div
            className="absolute inset-0 pointer-events-none rounded-xl transition-opacity duration-300 z-30"
            style={{
              background: `radial-gradient(circle at ${glarePosition.x}% ${glarePosition.y}%, rgba(255, 255, 255, ${glarePosition.opacity}), transparent 55%)`,
            }}
          />
        )}

        {/* 3D Content Wrapper */}
        <div style={{ transformStyle: 'preserve-3d' }}>
          {children}
        </div>
      </div>
    </div>
  );
};
