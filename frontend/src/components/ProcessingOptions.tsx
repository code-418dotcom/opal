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
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="flex items-center gap-2 mb-4">
        <Settings size={20} className="text-gray-600" />
        <h3 className="text-lg font-semibold">Processing Options</h3>
      </div>

      <p className="text-sm text-gray-600 mb-4">
        Choose which AI enhancements to apply to your images
      </p>

      <div className="space-y-4">
        {/* Background Removal */}
        <label className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer">
          <div className="flex-1">
            <div className="font-medium text-gray-900">Remove Background</div>
            <div className="text-sm text-gray-600">
              Extract product from background using Azure Computer Vision
            </div>
          </div>
          <div className="ml-4">
            <input
              type="checkbox"
              checked={options.remove_background}
              onChange={() => handleToggle('remove_background')}
              disabled={disabled}
              className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 cursor-pointer"
            />
          </div>
        </label>

        {/* Scene Generation */}
        <label className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer">
          <div className="flex-1">
            <div className="font-medium text-gray-900">Generate Lifestyle Scene</div>
            <div className="text-sm text-gray-600">
              Create AI-generated background and composite product into scene
            </div>
          </div>
          <div className="ml-4">
            <input
              type="checkbox"
              checked={options.generate_scene}
              onChange={() => handleToggle('generate_scene')}
              disabled={disabled}
              className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 cursor-pointer"
            />
          </div>
        </label>

        {/* Upscaling */}
        <label className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer">
          <div className="flex-1">
            <div className="font-medium text-gray-900">Upscale Image</div>
            <div className="text-sm text-gray-600">
              Enhance resolution using Real-ESRGAN (slower but higher quality)
            </div>
          </div>
          <div className="ml-4">
            <input
              type="checkbox"
              checked={options.upscale}
              onChange={() => handleToggle('upscale')}
              disabled={disabled}
              className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 cursor-pointer"
            />
          </div>
        </label>
      </div>

      {/* Info message */}
      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-800">
          💡 <strong>Tip:</strong> Disable features you don't need to speed up processing and reduce costs.
        </p>
      </div>
    </div>
  );
};

export default ProcessingOptions;
