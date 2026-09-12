import { defineConfig } from 'cypress';
export default defineConfig({
	e2e: {
		baseUrl: 'http://127.0.0.1:18871',
		specPattern: 'src/lib/components/custom/image-canvas/workflow.cy.js',
		supportFile: false
	},
	video: false,
	fixturesFolder: '.cache/image-canvas',
	screenshotsFolder: '.cache/image-canvas/screenshots',
	downloadsFolder: '.cache/image-canvas/downloads',
	defaultCommandTimeout: 20000
});
