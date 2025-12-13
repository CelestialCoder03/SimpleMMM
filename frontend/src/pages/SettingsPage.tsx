import { useTranslation } from 'react-i18next';
import { Header } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useUIStore } from '@/stores/uiStore';
import { changeLanguage, languages } from '@/i18n';

export function SettingsPage() {
  const { t, i18n } = useTranslation();
  const { theme, setTheme } = useUIStore();

  const currentLang = i18n.resolvedLanguage || i18n.language;

  return (
    <div className="flex flex-col">
      <Header title={t('common.settings')} />

      <div className="p-6 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>{t('common.settings')}</CardTitle>
            <CardDescription>{t('common.profile')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label>{t('settings.theme')}</Label>
              <Select value={theme} onValueChange={(v) => setTheme(v as 'light' | 'dark' | 'system')}>
                <SelectTrigger className="w-[220px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="system">{t('settings.themeSystem')}</SelectItem>
                  <SelectItem value="light">{t('settings.themeLight')}</SelectItem>
                  <SelectItem value="dark">{t('settings.themeDark')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>{t('settings.language')}</Label>
              <Select
                value={currentLang.startsWith('zh') ? 'zh-CN' : 'en'}
                onValueChange={(v) => changeLanguage(v)}
              >
                <SelectTrigger className="w-[220px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {languages.map((lang) => (
                    <SelectItem key={lang.code} value={lang.code}>
                      {lang.nativeName}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
