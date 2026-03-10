import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Lightbulb, X } from 'lucide-react';
import { usePreferences } from './PreferencesContext';
import type { Page } from './Sidebar';

interface Props {
  activePage: Page;
}

interface Tip {
  id: string;
  page: Page | 'all';
  text: string;
}

export default function TipsBar({ activePage }: Props) {
  const { t } = useTranslation();
  const { preferences, dismissTip } = usePreferences();

  const tips: Tip[] = useMemo(() => [
    { id: 'dashboard-welcome', page: 'dashboard', text: t('tips.dashboardWelcome', 'Start by uploading product images — Opal handles the rest!') },
    { id: 'upload-drag', page: 'upload', text: t('tips.uploadDrag', 'Drag & drop multiple images at once for batch processing.') },
    { id: 'upload-preset', page: 'upload', text: t('tips.uploadPreset', 'Use "Full Enhancement" for the best results — it combines all three processing steps.') },
    { id: 'upload-brand', page: 'upload', text: t('tips.uploadBrand', 'Select a brand profile to keep all your product images consistent.') },
    { id: 'results-export', page: 'results', text: t('tips.resultsExport', 'Download all images as a ZIP, or export in platform-specific sizes.') },
    { id: 'brands-tip', page: 'brands', text: t('tips.brandsTip', 'Brand profiles save your preferred style — colors, mood, and scenes are reused automatically.') },
    { id: 'integrations-tip', page: 'integrations', text: t('tips.integrationsTip', 'Connect your store to process and push images back without re-uploading.') },
    { id: 'ab-tests-tip', page: 'ab-tests', text: t('tips.abTestsTip', 'A/B test different product images on your live store to find what converts best.') },
    { id: 'benchmarks-tip', page: 'benchmarks', text: t('tips.benchmarksTip', 'Upload an image to get an instant quality score and improvement suggestions.') },
    { id: 'billing-tip', page: 'billing', text: t('tips.billingTip', 'Monthly plans save up to 35% compared to one-time packs.') },
  ], [t]);

  if (!preferences.show_tips_bar) return null;

  const available = tips.filter(
    tip => (tip.page === activePage || tip.page === 'all') && !preferences.dismissed_tips.includes(tip.id)
  );

  if (available.length === 0) return null;

  const tip = available[0];

  return (
    <div className="tips-bar">
      <Lightbulb size={16} className="tips-bar-icon" />
      <span className="tips-bar-text">{tip.text}</span>
      <button
        className="tips-bar-dismiss"
        onClick={() => dismissTip(tip.id)}
        title={t('common.dismiss', 'Dismiss')}
      >
        <X size={14} />
      </button>
    </div>
  );
}
