import { defineConfig } from 'cypress';

export default defineConfig({
	e2e: {
		baseUrl: 'http://127.0.0.1:18766',
		specPattern: 'src/lib/components/custom/welcome/composer.cy.js',
		supportFile: false
	},
	video: false,
	screenshotsFolder: '.cache/welcome/screenshots'
});
