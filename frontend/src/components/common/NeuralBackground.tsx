import React, { useEffect, useRef } from 'react';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  isAccent: boolean;
  pulsePhase: number;
}

export const NeuralBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);

    // Mouse coordinates
    let mouse = { x: -1000, y: -1000, radius: 160 };

    const handleMouseMove = (e: MouseEvent) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    };

    const handleMouseLeave = () => {
      mouse.x = -1000;
      mouse.y = -1000;
    };

    window.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseleave', handleMouseLeave);

    // Initialize particles
    const particleCount = Math.min(Math.floor((width * height) / 22000), 55);
    const particles: Particle[] = [];

    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.45,
        vy: (Math.random() - 0.5) * 0.45,
        radius: Math.random() * 1.8 + 1,
        isAccent: Math.random() < 0.18, // 18% accent nodes (Capital One red / glowing cyan)
        pulsePhase: Math.random() * Math.PI * 2,
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      // Update and draw particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        // Move
        p.x += p.vx;
        p.y += p.vy;

        // Bounce from boundaries
        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;

        // Interaction with mouse
        const dx = mouse.x - p.x;
        const dy = mouse.y - p.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < mouse.radius) {
          const force = (1 - dist / mouse.radius) * 0.02;
          p.x += dx * force;
          p.y += dy * force;
        }

        // Draw particle
        p.pulsePhase += 0.02;
        const pulse = Math.sin(p.pulsePhase) * 0.3 + 0.7;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius * pulse, 0, Math.PI * 2);
        if (p.isAccent) {
          ctx.fillStyle = `rgba(208, 48, 39, ${0.45 * pulse})`;
          ctx.shadowColor = '#D03027';
          ctx.shadowBlur = 8;
        } else {
          ctx.fillStyle = `rgba(56, 189, 248, ${0.35 * pulse})`;
          ctx.shadowColor = '#38BDF8';
          ctx.shadowBlur = 6;
        }
        ctx.fill();
        ctx.shadowBlur = 0;

        // Connect particles with filaments
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const distBetween = Math.hypot(p.x - p2.x, p.y - p2.y);
          const maxDist = 125;

          if (distBetween < maxDist) {
            const opacity = (1 - distBetween / maxDist) * 0.16;
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            if (p.isAccent || p2.isAccent) {
              ctx.strokeStyle = `rgba(208, 48, 39, ${opacity * 1.2})`;
            } else {
              ctx.strokeStyle = `rgba(0, 118, 190, ${opacity})`;
            }
            ctx.lineWidth = 0.8;
            ctx.stroke();
          }
        }

        // Connect to mouse if near
        if (dist < mouse.radius) {
          const mouseOpacity = (1 - dist / mouse.radius) * 0.28;
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(mouse.x, mouse.y);
          ctx.strokeStyle = `rgba(56, 189, 248, ${mouseOpacity})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }

      animationFrameId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-0 opacity-60"
      style={{ mixBlendMode: 'screen' }}
    />
  );
};
