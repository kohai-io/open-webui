import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

import { viteStaticCopy } from 'vite-plugin-static-copy';

export default defineConfig({
	plugins: [
		sveltekit(),
		viteStaticCopy({
			targets: [
				{
					src: 'node_modules/onnxruntime-web/dist/*.jsep.*',

					dest: 'wasm'
				}
			]
		})
	],
	define: {
		APP_VERSION: JSON.stringify(process.env.npm_package_version),
		APP_BUILD_HASH: JSON.stringify(process.env.APP_BUILD_HASH || 'dev-build')
	},
	server: {
		proxy: {
			// Proxy API calls to the backend to avoid CORS in dev
			'/api': {
				target: 'http://localhost:8080',
				changeOrigin: false,
				secure: false,
				ws: true
			},
			// Optional: OAuth and websocket endpoints
			'/oauth': {
				target: 'http://localhost:8080',
				changeOrigin: false,
				secure: false
			},
			'/ws': {
				target: 'http://localhost:8080',
				changeOrigin: false,
				secure: false,
				ws: true
			},
			'/openai': {
				target: 'http://localhost:8080',
				changeOrigin: false,
				secure: false,
				ws: false
			},
			'/ollama': {
				target: 'http://localhost:8080',
				changeOrigin: false,
				secure: false,
				ws: false
			}
		}
	},
	build: {
		sourcemap: true
	},
	worker: {
		format: 'es'
	},
	esbuild: {
		pure: process.env.ENV === 'dev' ? [] : ['console.log', 'console.debug', 'console.error']
	}
});
