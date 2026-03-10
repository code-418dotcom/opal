import { useTranslation } from 'react-i18next';
import { Coins } from 'lucide-react';
import type { ProcessingOptionsType } from './ProcessingOptions';

interface Props {
  fileCount: number;
  options: ProcessingOptionsType;
  sceneCount: number;
  angleCount: number;
}

export default function CostPreview({ fileCount, options, sceneCount, angleCount }: Props) {
  const { t } = useTranslation();

  if (fileCount === 0) return null;

  let imagesPerFile = 0;
  if (options.generate_scene) {
    const scenes = Math.max(1, sceneCount);
    const angles = Math.max(1, angleCount);
    imagesPerFile = scenes * angles;
  } else if (options.remove_background || options.upscale) {
    imagesPerFile = 1;
  }

  const totalImages = fileCount * Math.max(1, imagesPerFile);

  // Half credit when only 1 pipeline step is enabled
  const stepsEnabled = [options.remove_background, options.generate_scene, options.upscale].filter(Boolean).length;
  const cost = stepsEnabled <= 1 ? Math.max(1, Math.ceil(totalImages / 2)) : totalImages;

  return (
    <div className="cost-preview">
      <Coins size={16} className="cost-preview-icon" />
      <span className="cost-preview-text">
        {t('upload.jobCost', 'This job will cost {{count}} credit(s)', { count: cost })}
        {stepsEnabled <= 1 && totalImages > 1 && (
          <span className="cost-preview-detail">
            {' '}{t('upload.halfCreditNote', '(half credit per image with single step)')}
          </span>
        )}
      </span>
    </div>
  );
}
