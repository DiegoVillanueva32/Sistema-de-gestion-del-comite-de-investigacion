/**
 * Configuración de Tailwind CSS del Comité de Investigación.
 *
 * - Escanea las plantillas Jinja2 y app.js para generar solo las clases usadas.
 * - La paleta reproduce el tema "Nocturno": los neutros leen las variables CSS de
 *   static/style.css (así el modo impresión las puede cambiar) y los colores de
 *   acento usan hex para permitir opacidades como bg-accent/10.
 * - Preflight está desactivado porque style.css ya trae su propio reset.
 *
 * Compilar:  npm run build:css   (genera static/tailwind.css)
 * @type {import('tailwindcss').Config}
 */
module.exports = {
  // main.py se escanea porque el filtro clase_estado devuelve las clases st-*.
  content: ["./templates/**/*.html", "./static/app.js", "./main.py"],
  // Clases que las plantillas arman dinámicamente (alert-{{ categoria }}, prio-{{ prioridad }}).
  safelist: ["alert-success", "alert-error", "prio-alta", "prio-media", "prio-baja"],
  corePlugins: { preflight: false },
  theme: {
    extend: {
      colors: {
        bg: { DEFAULT: "var(--bg)", soft: "var(--bg-soft)" },
        surface: { DEFAULT: "var(--surface)", 2: "var(--surface-2)", 3: "var(--surface-3)" },
        line: { DEFAULT: "var(--border)", strong: "var(--border-strong)" },
        fg: "var(--text)",
        soft: "var(--text-soft)",
        muted: "var(--muted)",
        accent: { DEFAULT: "#2ee6a6", strong: "#1fcf91", ink: "#04130d" },
        info: "#38bdf8",
        danger: "#f43f5e",
        warn: "#fbbf24",
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "system-ui", "Arial", "sans-serif"],
        display: ["Space Grotesk", "Inter", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "Cascadia Mono", "Consolas", "monospace"],
      },
      borderRadius: { card: "14px", field: "9px" },
      boxShadow: {
        card: "0 10px 30px rgb(0 0 0 / 35%)",
        glow: "0 6px 22px rgb(46 230 166 / 28%)",
      },
      backgroundImage: {
        brand: "linear-gradient(135deg, #2ee6a6 0%, #38bdf8 100%)",
      },
      keyframes: {
        entrar: { from: { opacity: "0", transform: "translateY(-6px)" }, to: { opacity: "1", transform: "none" } },
      },
      animation: { entrar: "entrar .25s ease-out" },
    },
  },
};
