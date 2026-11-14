// ===== إعدادات اللعب الأونلاين =====
// عشان الغرف الأونلاين تشتغل بين الأجهزة، سو مشروع مجاني في https://supabase.com
// وبعدين من Project Settings > API انسخ:
//   - Project URL  وحطه في supabaseUrl
//   - anon public key  وحطه في supabaseKey
// (لو تركتها فاضية، الغرف تشتغل بس بين تبويبات نفس المتصفح للتجربة)
window.GAME_CONFIG = {
  supabaseUrl: '',
  supabaseKey: '',
};
