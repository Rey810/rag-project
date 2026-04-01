import type { FC } from "react";

export const FinancialLoadingIcon: FC<{ className?: string }> = ({
  className,
}) => (
  <svg
    width="12"
    height="12"
    viewBox="0 0 12 12"
    fill="none"
    className={className}
    aria-hidden="true"
  >
    {/* Three ascending bars */}
    <rect x="1" y="8" width="2" height="3" rx="0.5" fill="currentColor">
      <animate
        attributeName="height"
        values="3;5;3"
        dur="1.2s"
        begin="0s"
        repeatCount="indefinite"
      />
      <animate
        attributeName="y"
        values="8;6;8"
        dur="1.2s"
        begin="0s"
        repeatCount="indefinite"
      />
    </rect>
    <rect x="5" y="5" width="2" height="6" rx="0.5" fill="currentColor">
      <animate
        attributeName="height"
        values="6;3;6"
        dur="1.2s"
        begin="0.2s"
        repeatCount="indefinite"
      />
      <animate
        attributeName="y"
        values="5;8;5"
        dur="1.2s"
        begin="0.2s"
        repeatCount="indefinite"
      />
    </rect>
    <rect x="9" y="2" width="2" height="9" rx="0.5" fill="currentColor">
      <animate
        attributeName="height"
        values="9;5;9"
        dur="1.2s"
        begin="0.4s"
        repeatCount="indefinite"
      />
      <animate
        attributeName="y"
        values="2;6;2"
        dur="1.2s"
        begin="0.4s"
        repeatCount="indefinite"
      />
    </rect>
    {/* Trend line */}
    <line
      x1="1"
      y1="7"
      x2="11"
      y2="1.5"
      stroke="currentColor"
      strokeWidth="0.8"
      strokeLinecap="round"
      opacity="0.5"
    />
  </svg>
);
