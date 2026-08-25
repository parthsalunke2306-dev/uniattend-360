/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './frontend/**/*.{html,js,ts,jsx,tsx}',
    './app/**/*.{html,js,ts,jsx,tsx}',
    './*.{html,js,ts,jsx,tsx}'
  ],
  theme: {
    extend: {
      fontFamily: {
        serif: ['"Lora"', '"Playfair Display"', '"Georgia"', 'serif'],
        sans: ['"Plus Jakarta Sans"', '-apple-system', 'BlinkMacSystemFont', '"Inter"', 'sans-serif'],
        mono: ['"Geist Mono"', '"SF Mono"', 'monospace'],
      },
      colors: {
        // Organic Warm Cream & Porcelain Surfaces
        canvas: {
          DEFAULT: '#FBF9F5',       // Soft Warm Parchment Cream
          subtle: '#F4F0E8',        // Oat/Linen Canvas Accent
          muted: '#EFEAE0',
        },
        surface: {
          DEFAULT: '#FFFFFF',       // Pure Warm Card
          translucent: 'rgba(255, 255, 255, 0.92)',
          hover: '#F8F6F0',
        },
        elevated: {
          DEFAULT: '#F5F2EB',       // Soft Linen / Oatmeal Container
          subtle: '#ECE7DF',
        },
        border: {
          DEFAULT: '#E8E3DA',       // Low-Contrast Organic Stone Border
          subtle: 'rgba(90, 80, 60, 0.10)',
          hairline: '#DFD8CC',
          focus: '#2F5238',
        },
        // Deep Rich Espresso & Charcoal Typography
        text: {
          primary: '#1C241E',       // Deep Forest Dark Slate / Espresso
          secondary: '#5A655C',     // Muted Olive Slate
          muted: '#869288',         // Soft Botanical Gray
          light: '#A3ADA5',
        },
        // Organic Botanical & Earthy Accents
        forest: {
          DEFAULT: '#2F5238',       // Deep Forest Sage Green
          hover: '#25422D',
          light: '#3E6349',
          glow: 'rgba(47, 82, 56, 0.12)',
        },
        sage: {
          DEFAULT: '#4A6B53',       // Good Status Pill
          bg: '#EAF2EB',
          text: '#2D4F38',
          bar: '#47664B',
        },
        clay: {
          DEFAULT: '#8D3F30',       // Needs Care / Warning Pill
          bg: '#FCE4DA',
          text: '#8D3F30',
          bar: '#9E4D3D',
        },
        ochre: {
          DEFAULT: '#C28222',       // Warm Amber Ochre
          bg: '#FEF3DD',
          text: '#8C5B14',
        },
        // Semantic Compatibility Aliases
        stitch: {
          bg: '#FBF9F5',
          surface: '#FFFFFF',
          card: '#FFFFFF',
          border: '#E8E3DA',
          primary: '#2F5238',
          primaryGlow: 'rgba(47, 82, 56, 0.10)',
          emerald: '#4A6B53',
          emeraldGlow: 'rgba(74, 107, 83, 0.12)',
          amber: '#C28222',
          rose: '#8D3F30',
        },
        ios: {
          bg: '#FBF9F5',
          card: '#FFFFFF',
          cardTertiary: '#F5F2EB',
          separator: '#E8E3DA',
          blue: '#2F5238',
          green: '#4A6B53',
          orange: '#C28222',
          red: '#8D3F30',
          purple: '#6B5B95',
          yellow: '#D4A373',
          gray: '#869288',
          glass: 'rgba(255, 255, 255, 0.92)',
        },
        accent: {
          blue: {
            DEFAULT: '#2F5238',     // Mapped to Forest Sage
            glow: 'rgba(47, 82, 56, 0.12)',
            light: '#3E6349',
          },
          mint: {
            DEFAULT: '#4A6B53',     // Mapped to Sage Green
            glow: 'rgba(74, 107, 83, 0.12)',
            light: '#5A7F64',
          },
          amber: {
            DEFAULT: '#C28222',     // Mapped to Warm Ochre
            glow: 'rgba(194, 130, 34, 0.12)',
            light: '#D99632',
          },
          rose: {
            DEFAULT: '#8D3F30',     // Mapped to Terracotta Clay
            glow: 'rgba(141, 63, 48, 0.12)',
            light: '#A54F3E',
          },
          purple: {
            DEFAULT: '#5D4E6D',
            glow: 'rgba(93, 78, 109, 0.12)',
            light: '#726084',
          }
        }
      },
      boxShadow: {
        'soft-glow': '0 4px 20px -2px rgba(60, 70, 60, 0.06), 0 2px 6px -1px rgba(60, 70, 60, 0.03)',
        'organic-card': '0 4px 24px -2px rgba(50, 60, 50, 0.07), 0 1px 3px 0 rgba(50, 60, 50, 0.04)',
        'forest-glow': '0 0 18px rgba(47, 82, 56, 0.15)',
        'clay-glow': '0 0 18px rgba(141, 63, 48, 0.15)',
      }
    }
  },
  plugins: []
};
