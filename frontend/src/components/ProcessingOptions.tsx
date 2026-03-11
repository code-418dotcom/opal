import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Scissors, Sparkles, ArrowUpFromDot, ChevronDown, ChevronUp } from 'lucide-react';
import HelpTooltip from './HelpTooltip';

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

type Preset = 'full' | 'bg-only' | 'custom';

function getPreset(options: ProcessingOptionsType): Preset {
  if (options.remove_background && options.generate_scene && !options.upscale) return 'full';
  if (options.remove_background && !options.generate_scene && !options.upscale) return 'bg-only';
  return 'custom';
}

export const ProcessingOptions: React.FC<ProcessingOptionsProps> = ({
  options,
  onChange,
  disabled = false,
}) => {
  const { t } = useTranslation();
  const [preset, setPreset] = useState<Preset>(() => getPreset(options));
  const [showCustom, setShowCustom] = useState(false);

  useEffect(() => {
    setPreset(getPreset(options));
  }, [options]);

  const PRESETS: Array<{ id: Preset; label: string; description: string }> = [
    {
      id: 'full',
      label: t('processing.presetFull', 'Full Enhancement'),
      description: t('processing.presetFullDesc', 'Background removal + AI scene — best results'),
    },
    {
      id: 'bg-only',
      label: t('processing.presetBgOnly', 'Background Only'),
      description: t('processing.presetBgOnlyDesc', 'Just remove the background, keep everything else'),
    },
    {
      id: 'custom',
      label: t('processing.presetCustom', 'Custom'),
      description: t('processing.presetCustomDesc', 'Pick exactly which steps to run'),
    },
  ];

  const OPTIONS: Array<{
    key: keyof ProcessingOptionsType;
    icon: typeof Scissors;
    name: string;
    help: string;
  }> = [
    {
      key: 'remove_background',
      icon: Scissors,
      name: t('processing.removeBackground'),
      help: t('help.removeBackground', 'Removes the background from your product image, leaving a clean cutout on a transparent background.'),
    },
    {
      key: 'generate_scene',
      icon: Sparkles,
      name: t('processing.sceneGeneration'),
      help: t('help.sceneGeneration', 'Places your product in a professional AI-generated setting — like a marble countertop or lifestyle scene.'),
    },
    {
      key: 'upscale',
      icon: ArrowUpFromDot,
      name: t('processing.hdUpscale'),
      help: t('help.hdUpscale', 'Sharpens and upscales your image to HD quality, making it look crisp on any device.'),
    },
  ];

  const handlePreset = (id: Preset) => {
    setPreset(id);
    if (id === 'full') {
      onChange({ remove_background: true, generate_scene: true, upscale: false });
      setShowCustom(false);
    } else if (id === 'bg-only') {
      onChange({ remove_background: true, generate_scene: false, upscale: false });
      setShowCustom(false);
    } else {
      setShowCustom(true);
    }
  };

  const handleToggle = (key: keyof ProcessingOptionsType) => {
    onChange({ ...options, [key]: !options[key] });
  };

  return (
    <div className="processing-options">
      <h3 className="processing-options-title">
        {t('processing.title')}
        <HelpTooltip text={t('help.processingPipeline', 'Choose how your images are processed. Full Enhancement gives the best results for product listings.')} />
      </h3>

      <div className="processing-presets">
        {PRESETS.map(p => (
          <button
            key={p.id}
            className={`processing-preset ${preset === p.id ? 'active' : ''} ${disabled ? 'disabled' : ''}`}
            onClick={() => !disabled && handlePreset(p.id)}
          >
            <div className="processing-preset-label">{p.label}</div>
            <div className="processing-preset-desc">{p.description}</div>
          </button>
        ))}
      </div>

      {(preset === 'custom' || showCustom) && (
        <div className="processing-options-list">
          {OPTIONS.map((opt) => (
            <label key={opt.key} className={`processing-option ${disabled ? 'disabled' : ''}`}>
              <div className="processing-option-left">
                <opt.icon size={20} className="processing-option-icon" />
                <div className="processing-option-info">
                  <div className="processing-option-name">
                    {opt.name}
                    <HelpTooltip text={opt.help} />
                  </div>
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
      )}

      {preset !== 'custom' && !showCustom && (
        <button
          className="processing-customize-btn"
          onClick={() => { setPreset('custom'); setShowCustom(true); }}
        >
          {t('processing.customize', 'Customize')}
          <ChevronDown size={14} />
        </button>
      )}
      {showCustom && preset === 'custom' && (
        <button
          className="processing-customize-btn"
          onClick={() => setShowCustom(false)}
        >
          {t('processing.hideCustom', 'Hide options')}
          <ChevronUp size={14} />
        </button>
      )}
    </div>
  );
};

export default ProcessingOptions;
