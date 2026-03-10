import { useTranslation } from 'react-i18next';
import { HelpCircle, Lightbulb } from 'lucide-react';
import { usePreferences } from './PreferencesContext';

export default function SettingsPage() {
  const { t } = useTranslation();
  const { preferences, updatePreference } = usePreferences();

  return (
    <div className="settings-page">
      <div className="section-header">
        <h2>{t('settings.title', 'Settings')}</h2>
        <p>{t('settings.subtitle', 'Customize your Opal experience')}</p>
      </div>

      <div className="settings-section">
        <h3 className="settings-section-title">
          {t('settings.helpGuidance', 'Help & Guidance')}
        </h3>

        <label className="settings-toggle-row">
          <div className="settings-toggle-info">
            <HelpCircle size={20} className="settings-toggle-icon" />
            <div>
              <div className="settings-toggle-name">
                {t('settings.helpTooltips', 'Help Tooltips')}
              </div>
              <div className="settings-toggle-desc">
                {t('settings.helpTooltipsDesc', 'Show hoverable question marks that explain what each option does')}
              </div>
            </div>
          </div>
          <div
            className={`toggle-switch ${preferences.show_help_tooltips ? 'toggle-on' : ''}`}
            onClick={() => updatePreference('show_help_tooltips', !preferences.show_help_tooltips)}
          >
            <div className="toggle-thumb" />
          </div>
        </label>

        <label className="settings-toggle-row">
          <div className="settings-toggle-info">
            <Lightbulb size={20} className="settings-toggle-icon" />
            <div>
              <div className="settings-toggle-name">
                {t('settings.tipsBar', 'Tips Bar')}
              </div>
              <div className="settings-toggle-desc">
                {t('settings.tipsBarDesc', 'Show contextual tips and suggestions at the top of each page')}
              </div>
            </div>
          </div>
          <div
            className={`toggle-switch ${preferences.show_tips_bar ? 'toggle-on' : ''}`}
            onClick={() => updatePreference('show_tips_bar', !preferences.show_tips_bar)}
          >
            <div className="toggle-thumb" />
          </div>
        </label>
      </div>
    </div>
  );
}
