// إعدادات السيرفر للعب الأونلاين (Supabase Realtime)
// تقدر تحطها في public/config.js (بدون إعادة بناء) أو كمتغيرات بيئة وقت البناء
declare global {
  interface Window {
    GAME_CONFIG?: { supabaseUrl?: string; supabaseKey?: string };
  }
}

export const config = {
  supabaseUrl: (window.GAME_CONFIG?.supabaseUrl || import.meta.env.VITE_SUPABASE_URL || '').trim(),
  supabaseKey: (window.GAME_CONFIG?.supabaseKey || import.meta.env.VITE_SUPABASE_ANON_KEY || '').trim(),
};

export const onlineReady = () => !!(config.supabaseUrl && config.supabaseKey);
