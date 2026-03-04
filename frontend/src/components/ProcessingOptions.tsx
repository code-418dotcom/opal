import React from 'react';
import { Scissors, Sparkles, ArrowUpFromDot } from 'lucide-react';

export interface ProcessingOptionsType {
  remove_background: boolean;
  generate_scene: boolean;
  upscale: boolean;
}

interface ProcessingOptionsProps {
  options: ProcessingOptionsType;
  onChange: (options: ProcessingOptionsType) => void;
  disabled?: boolean;
}

const OPTIONS: Array<{
  key: keyof ProcessingOptionsType;
  icon: typeof Scissors;
  name: string;
  description: string;
}> = [
  {
    key: 'remove_background',
    icon: Scissors,
    name: 'Remove Background',
    description: 'Isolate your product with a transparent background',
  },
  {
    key: 'generate_scene',
    icon: Sparkles,
    name: 'AI Scene Generation',
    description: 'Place your product in a professional setting',
  },
  {
    key: 'upscale',
    icon: ArrowUpFromDot,
    name: 'HD Upscale',
    description: 'Enhance image resolution for print-ready quality',
  },
];

export const ProcessingOptions: React.FC<ProcessingOptionsProps> = ({
  options,
  onChange,
  disabled = false,
}) => {
  const handleToggle = (key: keyof ProcessingOptionsType) => {
    onChange({
      ...options,
      [key]: !options[key],
    });
  };

  return (
    <div className="processing-options">
      <h3 className="processing-options-title">Processing Pipeline</h3>

      <div className="processing-options-list">
        {OPTIONS.map((opt) => (
          <label key={opt.key} className={`processing-option ${disabled ? 'disabled' : ''}`}>
            <div className="processing-option-left">
              <opt.icon size={20} className="processing-option-icon" />
              <div className="processing-option-info">
                <div className="processing-option-name">{opt.name}</div>
                <div className="processing-option-desc">{opt.description}</div>
              </div>
            </div>
            <div
              className={`toggle-switch ${options[opt.key] ? 'toggle-on' : ''}`}
              onClick={(e) => {
                e.preventDefault();
                if (!disabled) handleToggle(opt.key);
              }}
            >
              <div className="toggle-thumb" />
            </div>
          </label>
        ))}
      </div>
    </div>
  );
};

export default ProcessingOptions;
