import { defineConfig } from 'vite';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	build: {
		sourcemap: true,
		minify: 'terser',
		target: 'esnext',
		cssTarget: 'esnext',
		chunkSizeWarningLimit: 2048,
		emptyOutDir: true
	}
});
