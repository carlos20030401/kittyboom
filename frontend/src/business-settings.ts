import { useCallback, useEffect, useState } from 'react';
import{API_URL}from'./config';

const API = API_URL;
export type BusinessSettings = { business_name?: string; whatsapp?: string | null; instagram?: string | null; tiktok?: string | null; address?: string | null; hours?: string | null; currency?: string; logo_url?: string | null };

export function useBusinessSettings() {
  const [settings, setSettings] = useState<BusinessSettings>({ business_name: 'KittyBoom', currency: 'S/' });
  const [loading, setLoading] = useState(true);
  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API}/public/settings`, { cache: 'no-store' });
      if (response.ok) setSettings(await response.json());
    } catch { /* La tienda conserva valores seguros mientras la API se inicia. */ }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void reload(); const handler = () => void reload(); window.addEventListener('kittyboom:settings-updated', handler); return () => window.removeEventListener('kittyboom:settings-updated', handler); }, [reload]);
  return { settings, loading, reload };
}
