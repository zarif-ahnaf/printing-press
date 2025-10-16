import { defineConfig } from 'vite';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	build: {
		minify: 'terser',
		terserOptions: {
			format: { comments: false },
			compress: {
				drop_console: true,
				drop_debugger: true,
				passes: 3
			},
			keep_classnames: false,
			keep_fnames: false
		},
		target: 'esnext',
		cssTarget: 'esnext',
		chunkSizeWarningLimit: 2048,
		emptyOutDir: true
	}
});
