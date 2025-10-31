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
			output: {
				ecma: 5,
				comments: false, // Remove all comments
				beautify: false // Ensure minified output
			}
		},
		target: 'es6',
		cssTarget: 'es6',
		chunkSizeWarningLimit: 2048,
		emptyOutDir: true
	}
});
