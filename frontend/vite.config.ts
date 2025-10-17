import { defineConfig } from 'vite';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	build: {
		minify: 'terser',
		terserOptions: {
			keep_classnames: false,
			keep_fnames: false,
			mangle: {
				toplevel: true,
				eval: true,
				module: true,
				safari10: false
			},
			output: {
				ecma: 2020,
				comments: false, // Remove all comments
				beautify: false // Ensure minified output
			}
		},
		target: 'esnext',
		cssTarget: 'esnext',
		chunkSizeWarningLimit: 2048,
		emptyOutDir: true
	}
});
