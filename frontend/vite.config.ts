import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	esbuild: {
		target: 'esnext',
		legalComments: 'external'
	},
	build: {
		commonjsOptions: {
			transformMixedEsModules: true
		},
		chunkSizeWarningLimit: 2048,
		emptyOutDir: true,
		target: 'esnext',
		cssTarget: 'esnext',
		minify: 'terser'
		//sourcemap: true
	}
});
