/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./index_sidebar.html", 
    "./workflows.html",
    "./virtual-chat.html",
    "./virtual-chat-test.html",
    "./audit-dashboard.html",
    "./js/**/*.js",
    "./*.js"
  ],
  darkMode: 'class', // Enable class-based dark mode
  theme: {
    extend: {
      // Safelist common dynamic color combinations for agents
      colors: {
        // Ensure all agent colors are available
        purple: {
          50: '#faf5ff',
          100: '#f3e8ff', 
          500: '#8b5cf6',
          700: '#7c3aed',
        },
        green: {
          50: '#f0fdf4',
          100: '#dcfce7',
          500: '#22c55e', 
          700: '#15803d',
        },
        blue: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6',
          700: '#1d4ed8',
        },
        red: {
          50: '#fef2f2',
          100: '#fee2e2',
          500: '#ef4444',
          700: '#b91c1c',
        },
        orange: {
          50: '#fff7ed',
          100: '#ffedd5',
          500: '#f97316',
          700: '#c2410c',
        },
        gray: {
          50: '#f9fafb',
          100: '#f3f4f6',
          500: '#6b7280',
          700: '#374151',
        }
      }
    },
  },
  plugins: [],
  // JIT mode with safelist for dynamic classes
  safelist: [
    // Agent background colors
    'bg-purple-100', 'bg-purple-500', 'text-purple-700', 'text-purple-800',
    'bg-green-100', 'bg-green-500', 'text-green-700', 'text-green-800', 
    'bg-blue-100', 'bg-blue-500', 'text-blue-700', 'text-blue-800',
    'bg-red-100', 'bg-red-500', 'text-red-700', 'text-red-800',
    'bg-orange-100', 'bg-orange-500', 'text-orange-700', 'text-orange-800',
    'bg-gray-100', 'bg-gray-500', 'text-gray-700', 'text-gray-800',
    // Dark mode variations
    'dark:bg-purple-900', 'dark:bg-green-900', 'dark:bg-blue-900',
    'dark:bg-red-900', 'dark:bg-orange-900', 'dark:bg-gray-900',
    'dark:text-purple-200', 'dark:text-green-200', 'dark:text-blue-200',
    'dark:text-red-200', 'dark:text-orange-200', 'dark:text-gray-200',
    // Hover and focus states
    'hover:bg-purple-200', 'hover:bg-green-200', 'hover:bg-blue-200',
    'hover:bg-red-200', 'hover:bg-orange-200', 'hover:bg-gray-200',
  ]
}

