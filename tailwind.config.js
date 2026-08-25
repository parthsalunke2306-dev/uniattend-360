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
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"Plus Jakarta Sans"',
          '"Inter"',
          'sans-serif'
        ],
        mono: ['"Geist Mono"', '"SF Mono"', 'monospace'],
      },
      colors: {
        // Semantic Canvas & Surface Tokens (Replacing Pitch-Black)
        canvas: {
          DEFAULT: '#181B22',       // Atmospheric Deep Slate Canvas
          subtle: '#1E222B',        // Slightly lighter background variant
        },
        surface: {
          DEFAULT: '#252A36',       // Luminous Charcoal Surface Card
          translucent: 'rgba(37, 42, 54, 0.75)', // Frosted glass surface
          hover: '#2A303E',          // Subtle hover state
        },
        elevated: {
          DEFAULT: '#313746',       // Warm Milled Slate (Inner Cards / Modals)
          subtle: '#373E4E',        // Elevated pill/badge background
        },
        border: {
          subtle: 'rgba(255, 255, 255, 0.08)', // Low-contrast hairline divider
          light: '#373E4E',                    // Solid subtle border
          focus: '#4F86F7',                    // Active focus ring
        },
        // Soothing Typography Tokens
        text: {
          primary: '#F1F5F9',       // Crisp Alabaster Pearl (High Readability, Low Fatigue)
          secondary: '#CBD5E1',     // Muted Light Slate for Body Copy
          muted: '#7C8BA1',         // Soft Cool Gray for Subtitles & Meta
        },
        // Eye-Friendly Soft Pastel & Glowing Accent Tokens
        accent: {
          blue: {
            DEFAULT: '#4F86F7',     // Electric Cornflower Blue
            glow: 'rgba(79, 134, 247, 0.15)',
            light: '#60A5FA',
          },
          mint: {
            DEFAULT: '#34D399',     // Soft Mint / Sage Green (Verified/Passkey)
            glow: 'rgba(52, 211, 153, 0.12)',
            light: '#4ADE80',
          },
          amber: {
            DEFAULT: '#FBBF24',     // Warm Amber Gold (Timer/Paused)
            glow: 'rgba(251, 191, 36, 0.12)',
            light: '#FCD34D',
          },
          rose: {
            DEFAULT: '#F87171',     // Coral Rose (Security Alerts / Proxy Flagged)
            glow: 'rgba(248, 113, 113, 0.12)',
            light: '#FB7185',
          },
          purple: {
            DEFAULT: '#A78BFA',     // Soft Lavender Indigo
            glow: 'rgba(167, 139, 250, 0.15)',
            light: '#C084FC',
          }
        },
        // Legacy alias mappings for backward compatibility
        stitch: {
          bg: '#181B22',
          surface: '#252A36',
          card: '#282D39',
          border: '#373E4E',
          primary: '#4F86F7',
          primaryGlow: 'rgba(79, 134, 247, 0.15)',
          emerald: '#34D399',
          emeraldGlow: 'rgba(52, 211, 153, 0.12)',
          amber: '#FBBF24',
          rose: '#F87171',
        },
        ios: {
          bg: '#181B22',
          card: '#252A36',
          cardTertiary: '#313746',
          separator: '#373E4E',
          blue: '#4F86F7',
          green: '#34D399',
          orange: '#FBBF24',
          red: '#F87171',
          purple: '#A78BFA',
          gray: '#7C8BA1',
          glass: 'rgba(37, 42, 54, 0.78)',
        }
      },
      boxShadow: {
        'soft-glow': '0 8px 32px rgba(10, 13, 18, 0.35)',
        'blue-glow': '0 0 20px rgba(79, 134, 247, 0.15)',
        'mint-glow': '0 0 20px rgba(52, 211, 153, 0.15)',
        'amber-glow': '0 0 20px rgba(251, 191, 36, 0.15)',
        'rose-glow': '0 0 20px rgba(248, 113, 113, 0.15)',
      },
      backdropBlur: {
        'xs': '2px',
        'subtle': '16px',
      }
    }
  },
  plugins: []
};
