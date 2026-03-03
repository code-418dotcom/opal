import React from 'react';
import { Settings } from 'lucide-react';

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

export const ProcessingOptions: React.FC<ProcessingOptionsProps> = ({
  options,
  onChange,
  disabled = false
}) => {
  const handleToggle = (key: keyof ProcessingOptionsType) => {
    onChange({
      ...options,
      [key]: !options[key]
    });
  };

  return (
    <div className="processing-options">
      <div className="processing-options-header">
        <Settings size={20} />
        <h3>Processing Options</h3>
      </div>

      <p className="processing-options-desc">
        Choose which AI enhancements to apply to your images
      </p>

      <div className="processing-options-list">
        <label className="processing-option">
          <div className="processing-option-info">
            <div className="processing-option-name">Remove Background</div>
            <div className="processing-option-desc">
              Extract product from background using Azure Computer Vision
            </div>
          </div>
          <input
            type="checkbox"
            checked={options.remove_background}
            onChange={() => handleToggle('remove_background')}
            disabled={disabled}
          />
        </label>

        <label className="processing-option">
          <div className="processing-option-info">
            <div className="processing-option-name">Generate Lifestyle Scene</div>
            <div className="processing-option-desc">
              Create AI-generated background and composite product into scene
            </div>
          </div>
          <input
            type="checkbox"
            checked={options.generate_scene}
            onChange={() => handleToggle('generate_scene')}
            disabled={disabled}
          />
        </label>

        <label className="processing-option">
          <div className="processing-option-info">
            <div className="processing-option-name">Upscale Image</div>
            <div className="processing-option-desc">
              Enhance resolution using Real-ESRGAN (slower but higher quality)
            </div>
          </div>
          <input
            type="checkbox"
            checked={options.upscale}
            onChange={() => handleToggle('upscale')}
            disabled={disabled}
          />
        </label>
      </div>

      <div className="processing-option-tip">
        <p>
          Tip: Disable features you don't need to speed up processing and reduce costs.
        </p>
      </div>
    </div>
  );
};

export default ProcessingOptions;
