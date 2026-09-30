import React from 'react';

interface GraphMotifProps {
  className?: string;
  size?: number;
}

export const GraphMotif: React.FC<GraphMotifProps> = ({
  className = '',
  size = 200,
}) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 200 200"
      className={className}
      style={{ opacity: 0.8 }}
    >
      {/* Dashed connection lines */}
      <g strokeDasharray="3,3" strokeWidth="1.5" opacity="0.3">
        <line x1="60" y1="50" x2="100" y2="100" stroke="currentColor" />
        <line x1="140" y1="60" x2="100" y2="100" stroke="currentColor" />
        <line x1="100" y1="100" x2="60" y2="150" stroke="currentColor" />
        <line x1="100" y1="100" x2="140" y2="150" stroke="currentColor" />
        <line x1="60" y1="50" x2="140" y2="60" stroke="currentColor" />
      </g>

      {/* Active nodes (filled bronze) */}
      {/* Top left */}
      <circle cx="60" cy="50" r="8" fill="#c17f3e" opacity="0.9" />
      <circle cx="60" cy="50" r="6" fill="#d4934a" opacity="0.6" />

      {/* Center */}
      <circle cx="100" cy="100" r="10" fill="#c17f3e" opacity="0.95" />
      <circle cx="100" cy="100" r="7" fill="#d4934a" opacity="0.7" />

      {/* Inactive nodes (hollow warm brown) */}
      {/* Top right */}
      <circle
        cx="140"
        cy="60"
        r="8"
        fill="none"
        stroke="#5b5443"
        strokeWidth="1.5"
        opacity="0.5"
      />

      {/* Bottom left */}
      <circle
        cx="60"
        cy="150"
        r="8"
        fill="none"
        stroke="#5b5443"
        strokeWidth="1.5"
        opacity="0.5"
      />

      {/* Bottom right */}
      <circle
        cx="140"
        cy="150"
        r="8"
        fill="none"
        stroke="#5b5443"
        strokeWidth="1.5"
        opacity="0.5"
      />

      {/* Optional: subtle glow around center node */}
      <circle
        cx="100"
        cy="100"
        r="14"
        fill="none"
        stroke="#c17f3e"
        strokeWidth="0.5"
        opacity="0.2"
      />
    </svg>
  );
};
