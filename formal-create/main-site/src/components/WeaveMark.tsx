type WeaveMarkProps = {
  className?: string;
};

export default function WeaveMark({ className = "h-4 w-4" }: WeaveMarkProps) {
  return (
    <svg
      viewBox="0 0 32 32"
      aria-hidden="true"
      className={className}
      fill="none"
    >
      <path
        d="M7 10.5C10.9 5.9 17.8 5.2 23 8.9"
        stroke="url(#weave-a)"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        d="M6.5 16.2C10.4 12.6 15.9 12 20.4 14.6C22.2 15.6 23.5 17 25.5 20.4"
        stroke="url(#weave-b)"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        d="M8.2 22.4C13.7 25.9 20.1 24.9 24.9 19.7"
        stroke="url(#weave-c)"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <circle cx="16" cy="16" r="4.2" fill="url(#weave-core)" />
      <circle cx="16" cy="16" r="1.55" fill="white" fillOpacity="0.92" />
      <circle cx="7" cy="10.5" r="1.8" fill="#93B2FF" />
      <circle cx="25.5" cy="20.4" r="1.8" fill="#8B5CF6" />
      <defs>
        <linearGradient id="weave-a" x1="7" y1="10.5" x2="23" y2="8.9">
          <stop stopColor="#EAF0FF" />
          <stop offset="0.48" stopColor="#93B2FF" />
          <stop offset="1" stopColor="#8B5CF6" />
        </linearGradient>
        <linearGradient id="weave-b" x1="6.5" y1="16.2" x2="25.5" y2="20.4">
          <stop stopColor="#22D3EE" />
          <stop offset="0.55" stopColor="#6087FF" />
          <stop offset="1" stopColor="#A78BFA" />
        </linearGradient>
        <linearGradient id="weave-c" x1="8.2" y1="22.4" x2="24.9" y2="19.7">
          <stop stopColor="#DCE6FF" />
          <stop offset="0.5" stopColor="#3B5FFF" />
          <stop offset="1" stopColor="#EC4899" />
        </linearGradient>
        <radialGradient id="weave-core" cx="0" cy="0" r="1" gradientTransform="translate(14.4 14.2) rotate(47.7) scale(8.5)">
          <stop stopColor="white" />
          <stop offset="0.33" stopColor="#93B2FF" />
          <stop offset="0.72" stopColor="#3B5FFF" />
          <stop offset="1" stopColor="#8B5CF6" />
        </radialGradient>
      </defs>
    </svg>
  );
}
