import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQueryClient } from '@tanstack/react-query';
import {
  ChevronRight,
  ChevronLeft,
  Check,
  Loader,
  Sparkles,
  Store,
  Palette,
  X,
} from 'lucide-react';
import { api } from '../api';

const PRODUCT_CATEGORIES = [
  'Jewelry & Accessories',
  'Clothing & Apparel',
  'Shoes & Footwear',
  'Beauty & Skincare',
  'Food & Beverages',
  'Electronics & Gadgets',
  'Home & Furniture',
  'Toys & Games',
  'Sports & Outdoor',
  'Art & Handmade',
] as const;

const MOODS = ['modern', 'rustic', 'luxury', 'minimal', 'playful', 'professional'] as const;

const PRESET_PALETTES = [
  { name: 'Ocean', colors: ['#0ea5e9', '#06b6d4', '#14b8a6'] },
  { name: 'Sunset', colors: ['#f97316', '#ef4444', '#eab308'] },
  { name: 'Forest', colors: ['#22c55e', '#15803d', '#a3e635'] },
  { name: 'Royal', colors: ['#8b5cf6', '#6366f1', '#a78bfa'] },
  { name: 'Earth', colors: ['#92400e', '#d97706', '#78716c'] },
  { name: 'Rose', colors: ['#f43f5e', '#ec4899', '#fb7185'] },
  { name: 'Night', colors: ['#1e293b', '#475569', '#64748b'] },
  { name: 'Custom', colors: ['#2563eb', '#10b981', '#f59e0b'] },
];

interface Props {
  onComplete: () => void;
}

export default function OnboardingWizard({ onComplete }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(0);
  const [brandName, setBrandName] = useState('');
  const [category, setCategory] = useState('');
  const [mood, setMood] = useState('');
  const [selectedPalette, setSelectedPalette] = useState(7); // Custom
  const [customColors, setCustomColors] = useState(['#2563eb', '#10b981', '#f59e0b']);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalSteps = 4;

  const currentColors = selectedPalette < PRESET_PALETTES.length - 1
    ? PRESET_PALETTES[selectedPalette].colors
    : customColors;

  const canProceed = () => {
    if (step === 0) return brandName.trim().length > 0;
    if (step === 1) return category.length > 0;
    return true;
  };

  const handleFinish = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.createBrandProfile({
        name: brandName.trim(),
        product_category: category || undefined,
        mood: mood || undefined,
        color_palette: currentColors,
        style_keywords: [],
        default_scene_count: 1,
      });
      queryClient.invalidateQueries({ queryKey: ['brand-profiles'] });
      onComplete();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create brand profile');
      setSaving(false);
    }
  };

  const handleSkip = () => {
    onComplete();
  };

  return (
    <div className="onboarding-overlay">
      <div className="onboarding-wizard">
        <button className="onboarding-skip" onClick={handleSkip}>
          {t('onboarding.skip', { defaultValue: 'Skip setup' })}
          <X size={14} />
        </button>

        {/* Progress Dots */}
        <div className="onboarding-progress">
          {Array.from({ length: totalSteps }).map((_, i) => (
            <div
              key={i}
              className={`onboarding-dot ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}
            />
          ))}
        </div>

        {/* Step 0: Brand Name */}
        {step === 0 && (
          <div className="onboarding-step">
            <div className="onboarding-step-icon">
              <Sparkles size={32} />
            </div>
            <h2>{t('onboarding.welcomeTitle', { defaultValue: "Let's set up your workspace" })}</h2>
            <p className="onboarding-desc">
              {t('onboarding.welcomeDesc', { defaultValue: 'Start by naming your brand. This helps us tailor scenes and backgrounds to your products.' })}
            </p>
            <div className="onboarding-field">
              <label>{t('onboarding.brandName', { defaultValue: 'Brand Name' })}</label>
              <input
                className="onboarding-input"
                placeholder={t('onboarding.brandPlaceholder', { defaultValue: 'e.g., My Store' })}
                value={brandName}
                onChange={e => setBrandName(e.target.value)}
                autoFocus
                onKeyDown={e => e.key === 'Enter' && canProceed() && setStep(1)}
              />
            </div>
          </div>
        )}

        {/* Step 1: Category */}
        {step === 1 && (
          <div className="onboarding-step">
            <div className="onboarding-step-icon">
              <Store size={32} />
            </div>
            <h2>{t('onboarding.categoryTitle', { defaultValue: 'What do you sell?' })}</h2>
            <p className="onboarding-desc">
              {t('onboarding.categoryDesc', { defaultValue: 'We use this to pick the right surfaces and backgrounds for your product photos.' })}
            </p>
            <div className="onboarding-category-grid">
              {PRODUCT_CATEGORIES.map(cat => (
                <button
                  key={cat}
                  className={`onboarding-category-btn ${category === cat ? 'selected' : ''}`}
                  onClick={() => setCategory(c => c === cat ? '' : cat)}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Color Palette */}
        {step === 2 && (
          <div className="onboarding-step">
            <div className="onboarding-step-icon">
              <Palette size={32} />
            </div>
            <h2>{t('onboarding.paletteTitle', { defaultValue: 'Pick your brand colors' })}</h2>
            <p className="onboarding-desc">
              {t('onboarding.paletteDesc', { defaultValue: 'Choose a preset or create your own palette. These guide scene generation.' })}
            </p>
            <div className="onboarding-palette-grid">
              {PRESET_PALETTES.map((pal, i) => (
                <button
                  key={pal.name}
                  className={`onboarding-palette-btn ${selectedPalette === i ? 'selected' : ''}`}
                  onClick={() => setSelectedPalette(i)}
                >
                  <div className="onboarding-palette-swatches">
                    {(i === PRESET_PALETTES.length - 1 ? customColors : pal.colors).map((c, j) => (
                      <span key={j} className="onboarding-swatch" style={{ background: c }} />
                    ))}
                  </div>
                  <span className="onboarding-palette-name">{pal.name}</span>
                </button>
              ))}
            </div>
            {selectedPalette === PRESET_PALETTES.length - 1 && (
              <div className="onboarding-custom-colors">
                {customColors.map((c, i) => (
                  <div key={i} className="onboarding-color-input">
                    <input
                      type="color"
                      value={c}
                      onChange={e => {
                        const next = [...customColors];
                        next[i] = e.target.value;
                        setCustomColors(next);
                      }}
                    />
                    <input
                      className="onboarding-hex-input"
                      value={c}
                      onChange={e => {
                        const next = [...customColors];
                        next[i] = e.target.value;
                        setCustomColors(next);
                      }}
                      maxLength={7}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Step 3: Mood */}
        {step === 3 && (
          <div className="onboarding-step">
            <div className="onboarding-step-icon">
              <Sparkles size={32} />
            </div>
            <h2>{t('onboarding.moodTitle', { defaultValue: 'What vibe fits your brand?' })}</h2>
            <p className="onboarding-desc">
              {t('onboarding.moodDesc', { defaultValue: 'This shapes the lighting and atmosphere of generated scenes. You can change this later.' })}
            </p>
            <div className="onboarding-mood-grid">
              {MOODS.map(m => (
                <button
                  key={m}
                  className={`onboarding-mood-btn ${mood === m ? 'selected' : ''}`}
                  onClick={() => setMood(prev => prev === m ? '' : m)}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="onboarding-error">
            {error}
          </div>
        )}

        {/* Navigation */}
        <div className="onboarding-nav">
          {step > 0 ? (
            <button className="onboarding-back" onClick={() => setStep(s => s - 1)}>
              <ChevronLeft size={16} /> {t('common.back', { defaultValue: 'Back' })}
            </button>
          ) : (
            <div />
          )}

          {step < totalSteps - 1 ? (
            <button
              className="onboarding-next"
              onClick={() => setStep(s => s + 1)}
              disabled={!canProceed()}
            >
              {t('common.next', { defaultValue: 'Next' })} <ChevronRight size={16} />
            </button>
          ) : (
            <button
              className="onboarding-finish"
              onClick={handleFinish}
              disabled={saving}
            >
              {saving ? (
                <><Loader className="spinning" size={14} /> {t('onboarding.creating', { defaultValue: 'Creating...' })}</>
              ) : (
                <><Check size={16} /> {t('onboarding.finish', { defaultValue: 'Get Started' })}</>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
