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

  // Each enabled step produces output images that cost 1 token each
  // Scene generation with multiple scenes/angles multiplies the count
  let imagesPerFile = 0;
  if (options.remove_background) imagesPerFile = 1;
  if (options.generate_scene) {
    const scenes = Math.max(1, sceneCount);
    const angles = Math.max(1, angleCount);
    imagesPerFile = scenes * angles;
  }
  if (!options.remove_background && !options.generate_scene && options.upscale) {
    imagesPerFile = 1;
  }

  const totalImages = fileCount * Math.max(1, imagesPerFile);

  return (
    <div className="cost-preview">
      <Coins size={16} className="cost-preview-icon" />
      <span className="cost-preview-text">
        {t('upload.costEstimate', 'Estimated cost: {{count}} token(s)', { count: totalImages })}
        {fileCount > 1 && (
          <span className="cost-preview-detail">
            {' '}({fileCount} {t('upload.images', 'images')} × {Math.max(1, imagesPerFile)} {t('upload.outputsEach', 'output(s) each')})
          </span>
        )}
      </span>
    </div>
  );
}
