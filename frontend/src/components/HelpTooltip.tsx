import { useState, useRef, useEffect } from 'react';
import { HelpCircle } from 'lucide-react';
import { usePreferences } from './PreferencesContext';

interface Props {
  text: string;
  position?: 'top' | 'bottom' | 'left' | 'right';
}

export default function HelpTooltip({ text, position = 'top' }: Props) {
  const { preferences } = usePreferences();
  const [visible, setVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const tooltipRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  if (!preferences.show_help_tooltips) return null;

  return (
    <span
      className="help-tooltip-wrapper"
      onMouseEnter={() => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        setVisible(true);
      }}
      onMouseLeave={() => {
        timeoutRef.current = setTimeout(() => setVisible(false), 150);
      }}
    >
      <HelpCircle size={14} className="help-tooltip-icon" />
      {visible && (
        <div ref={tooltipRef} className={`help-tooltip-popover help-tooltip-${position}`}>
          {text}
        </div>
      )}
    </span>
  );
}
