/** Inline SVG opal gem logo — renders at any size via width/height props */
export function OpalLogo({ size = 24 }: { size?: number }) {
  return (
    <svg viewBox="0 0 512 512" width={size} height={size} aria-label="Opal" style={{ display: 'inline-block', verticalAlign: 'middle' }}>
      <defs>
        <linearGradient id="sa-a" x1="0%" y1="10%" x2="90%" y2="95%">
          <stop offset="0%" stopColor="#7ae0ff"/>
          <stop offset="30%" stopColor="#4dc9f6"/>
          <stop offset="65%" stopColor="#7c6cf7"/>
          <stop offset="100%" stopColor="#5b21b6"/>
        </linearGradient>
        <linearGradient id="sa-b" x1="100%" y1="10%" x2="10%" y2="95%">
          <stop offset="0%" stopColor="#fbbf24"/>
          <stop offset="25%" stopColor="#f97316"/>
          <stop offset="60%" stopColor="#0ea5e9"/>
          <stop offset="100%" stopColor="#0e7490"/>
        </linearGradient>
        <radialGradient id="sa-c" cx="48%" cy="35%" r="28%">
          <stop offset="0%" stopColor="#fff" stopOpacity=".35"/>
          <stop offset="30%" stopColor="#e0e7ff" stopOpacity=".15"/>
          <stop offset="100%" stopColor="#7c3aed" stopOpacity="0"/>
        </radialGradient>
        <linearGradient id="sa-s" x1="50%" y1="0%" x2="50%" y2="100%">
          <stop offset="0%" stopColor="#fff" stopOpacity=".7"/>
          <stop offset="40%" stopColor="#fff" stopOpacity=".05"/>
          <stop offset="60%" stopColor="#fff" stopOpacity=".05"/>
          <stop offset="100%" stopColor="#fff" stopOpacity=".6"/>
        </linearGradient>
        <linearGradient id="sa-r" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#67e8f9" stopOpacity=".6"/>
          <stop offset="50%" stopColor="#fff" stopOpacity=".08"/>
          <stop offset="100%" stopColor="#22d3ee" stopOpacity=".5"/>
        </linearGradient>
        <clipPath id="sa-g">
          <path d="M256 62C300 62 340 82 368 118C396 154 410 206 410 268C410 330 396 382 368 418C340 454 300 474 256 474C212 474 172 454 144 418C116 382 102 330 102 268C102 206 116 154 144 118C172 82 212 62 256 62Z"/>
        </clipPath>
      </defs>
      <path d="M256 62C212 62 172 82 144 118C116 154 102 206 102 268C102 330 116 382 144 418C172 454 212 474 256 474Z" fill="url(#sa-a)"/>
      <path d="M256 62C300 62 340 82 368 118C396 154 410 206 410 268C410 330 396 382 368 418C340 454 300 474 256 474Z" fill="url(#sa-b)"/>
      <ellipse cx="246" cy="205" rx="120" ry="100" fill="url(#sa-c)" clipPath="url(#sa-g)"/>
      <line x1="256" y1="62" x2="256" y2="474" stroke="url(#sa-s)" strokeWidth="2"/>
      <path d="M256 62C300 62 340 82 368 118C396 154 410 206 410 268C410 330 396 382 368 418C340 454 300 474 256 474C212 474 172 454 144 418C116 382 102 330 102 268C102 206 116 154 144 118C172 82 212 62 256 62Z" fill="none" stroke="url(#sa-r)" strokeWidth="2"/>
    </svg>
  );
}
