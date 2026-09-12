/// <reference types="cypress" />
// All generation and file requests are mocked; these tests never spend model credits.
describe('Image canvas workflows', () => {
	/** @type {{image: string, prompt: string}[]} */
	let edits = [];
	/** @type {{prompt: string}[]} */
	let generations = [];
	let denyEdit = false,
		generationEnabled = true,
		editEnabled = true;
	/** @param {string} colour */
	const png = (colour) => {
		const canvas = document.createElement('canvas');
		canvas.width = canvas.height = 100;
		const ctx = canvas.getContext('2d');
		if (!ctx) throw new Error('Canvas 2D context unavailable');
		ctx.fillStyle = colour;
		ctx.fillRect(0, 0, 100, 100);
		return canvas.toDataURL('image/png');
	};
	/** @param {string} name @param {string} colour */
	const imageFile = (name, colour) => ({
		contents: Cypress.Buffer.from(png(colour).split(',')[1], 'base64'),
		fileName: name,
		mimeType: 'image/png'
	});
	/** @param {string} src */
	const pixels = async (src) => {
		const image = new Image();
		image.src = src;
		await image.decode();
		const canvas = document.createElement('canvas');
		canvas.width = image.width;
		canvas.height = image.height;
		const ctx = canvas.getContext('2d');
		if (!ctx) throw new Error('Canvas 2D context unavailable');
		ctx.drawImage(image, 0, 0);
		return {
			width: image.width,
			height: image.height,
			data: ctx.getImageData(0, 0, image.width, image.height).data
		};
	};
	const layers = () => cy.get('aside[aria-label="Canvas layers"] .layer-list button');
	const draw = () => {
		cy.contains('button', /^Draw$/).click();
		cy.get('[data-testid="image-canvas"] canvas').then(($canvas) => {
			const canvas = $canvas[0];
			const rect = canvas.getBoundingClientRect();
			/** @param {string} type @param {number} x @param {number} y @param {number} buttons */
			const dispatch = (type, x, y, buttons) =>
				canvas.dispatchEvent(
					new PointerEvent(type, {
						bubbles: true,
						pointerId: 1,
						isPrimary: true,
						pointerType: 'mouse',
						button: 0,
						buttons,
						clientX: rect.left + rect.width * x,
						clientY: rect.top + rect.height * y
					})
				);
			dispatch('pointerdown', 0.2, 0.2, 1);
			dispatch('pointermove', 0.5, 0.5, 1);
			dispatch('pointermove', 0.8, 0.2, 1);
			dispatch('pointerup', 0.8, 0.2, 0);
		});
	};
	beforeEach(() => {
		edits = [];
		generations = [];
		denyEdit = false;
		generationEnabled = true;
		editEnabled = true;
		cy.writeFile('.cache/image-canvas/generated.png', png('#22c55e').split(',')[1], 'base64');
		cy.intercept('**/ws/**', { statusCode: 503, body: '' });
		cy.intercept('**/api/**', (request) => {
			const path = new URL(request.url).pathname;
			if (path === '/api/config')
				return request.reply({
					name: 'Open WebUI',
					version: '0.10.2',
					features: { enable_websocket: false, enable_image_generation: true },
					audio: { stt: {}, tts: {} }
				});
			if (path === '/api/v1/auths/')
				return request.reply({
					id: 'canvas-test',
					name: 'Canvas Tester',
					email: 'canvas@example.test',
					role: 'admin',
					permissions: { workspace: {}, chat: {} }
				});
			if (path === '/api/v1/users/user/settings')
				return request.reply({ ui: { showChangelog: false } });
			if (path === '/api/models') return request.reply({ data: [] });
			if (path === '/api/v1/images/config')
				return request.reply({
					ENABLE_IMAGE_GENERATION: generationEnabled,
					ENABLE_IMAGE_EDIT: editEnabled
				});
			if (path === '/api/v1/images/generations') {
				generations.push(request.body);
				return request.reply([
					{ url: '/api/v1/files/generated/content' },
					{ url: '/api/v1/files/variation/content' }
				]);
			}
			if (path === '/api/v1/images/edit') {
				edits.push(request.body);
				if (denyEdit)
					return request.reply({ statusCode: 403, body: { detail: 'Image editing is disabled' } });
				return request.reply([{ url: '/api/v1/files/edited/content' }]);
			}
			if (path.endsWith('/content'))
				return request.reply({
					headers: { 'content-type': 'image/png' },
					fixture: 'generated.png,null'
				});
			return request.reply([]);
		});
	});
	const visit = () => {
		cy.visit('/playground/images', {
			onBeforeLoad(window) {
				window.localStorage.setItem('token', 'canvas-test-token');
				window.localStorage.setItem('locale', 'en-US');
				window.localStorage.setItem('sidebar', 'false');
				window.indexedDB.deleteDatabase('owui-image-canvas');
			}
		});
		cy.contains('button', 'Add images').should('be.enabled');
	};

	it('generates from text, puts the result on the canvas and lets other results join it', () => {
		cy.viewport(1440, 1000);
		visit();
		cy.get('#canvas-prompt').type('A green landscape');
		cy.contains('button', 'Generate from text').click();
		layers().should('have.length', 1);
		cy.get('section[aria-label="Generated images"] article').should('have.length', 2);
		cy.then(() => expect(generations).to.deep.equal([{ prompt: 'A green landscape' }]));
		cy.contains('button', 'Add to canvas').click();
		layers().should('have.length', 2);
		cy.screenshot('text-results-desktop');
	});

	it('combines two uploaded images into one PNG, preserves pixels and restores the editable inputs with undo', () => {
		cy.viewport(1440, 1000);
		visit();
		cy.get('input[type=file]').selectFile(
			[imageFile('red.png', '#ff0000'), imageFile('blue.png', '#0000ff')],
			{ force: true }
		);
		layers().should('have.length', 2);
		cy.get('[data-testid="image-canvas"] canvas').then(($canvas) => {
			const rect = $canvas[0].getBoundingClientRect();
			cy.wrap($canvas)
				.trigger('mousedown', {
					clientX: rect.left + rect.width * 0.5,
					clientY: rect.top + rect.height * 0.5,
					button: 0,
					buttons: 1
				})
				.trigger('mousemove', {
					clientX: rect.left + rect.width * 0.55,
					clientY: rect.top + rect.height * 0.55,
					buttons: 1
				})
				.trigger('mousemove', {
					clientX: rect.left + rect.width * 0.6,
					clientY: rect.top + rect.height * 0.6,
					buttons: 1
				})
				.trigger('mouseup', {
					clientX: rect.left + rect.width * 0.6,
					clientY: rect.top + rect.height * 0.6,
					button: 0,
					buttons: 0
				});
		});
		cy.get('#canvas-prompt').type('Combine the red and blue images');
		cy.contains('button', 'Generate from canvas').click();
		layers().should('have.length', 1);
		cy.then(async () => {
			expect(edits).to.have.length(1);
			expect(edits[0]).to.have.keys('image', 'prompt');
			const exported = await pixels(edits[0].image);
			expect(exported.width).to.equal(1024);
			expect(exported.height).to.equal(1024);
			const values = exported.data;
			let red = 0,
				blue = 0;
			// The blue layer moved down/right: this pixel was red before the drag.
			expect(
				Array.from(values.slice((800 * 1024 + 800) * 4, (800 * 1024 + 800) * 4 + 4))
			).to.deep.equal([0, 0, 255, 255]);
			for (let i = 0; i < values.length; i += 4) {
				if (values[i] === 255 && values[i + 2] === 0) red++;
				if (values[i] === 0 && values[i + 2] === 255) blue++;
			}
			expect(red).to.be.greaterThan(10000);
			expect(blue).to.be.greaterThan(10000);
		});
		cy.contains('button', /^Undo$/).click();
		layers().should('have.length', 2);
		cy.contains('button', /^Redo$/).click();
		layers().should('have.length', 1);
	});

	it('draws, persists after reload, generates from sketch pixels and retains the sketch on failure', () => {
		cy.viewport(1200, 900);
		visit();
		draw();
		layers().should('have.length', 1).and('contain', 'Drawing');
		cy.get('#canvas-prompt').type('Turn my drawing into a mountain');
		cy.reload();
		cy.contains('button', 'Add images').should('be.enabled');
		layers().should('have.length', 1);
		cy.get('#canvas-prompt').should('have.value', 'Turn my drawing into a mountain');
		cy.then(() => {
			denyEdit = true;
		});
		cy.contains('button', 'Generate from canvas').click();
		cy.get('[role=alert]').should('contain', 'Image editing is disabled');
		layers().should('have.length', 1).and('contain', 'Drawing');
		cy.then(async () => {
			const { data } = await pixels(edits[0].image);
			let ink = 0;
			for (let i = 0; i < data.length; i += 4)
				if (data[i] < 100 && data[i + 1] < 100 && data[i + 2] < 100) ink++;
			expect(ink).to.be.greaterThan(1000);
		});
		cy.then(() => {
			denyEdit = false;
		});
		cy.contains('button', 'Generate from canvas').click();
		layers().should('have.length', 1).and('not.contain', 'Drawing');
	});

	it('supports resize, layer ordering, removal and an undoable clear on a narrow screen', () => {
		cy.viewport(390, 844);
		visit();
		cy.get('input[type=file]').selectFile(
			[imageFile('red.png', '#ff0000'), imageFile('blue.png', '#0000ff')],
			{ force: true }
		);
		layers().should('have.length', 2);
		cy.get('input[type=number]').clear().type('50').blur();
		cy.contains('button', /^Backward$/).click();
		layers().first().should('contain', 'red.png');
		cy.contains('button', /^Remove$/).click();
		layers().should('have.length', 1);
		cy.contains('button', 'Clear canvas').click();
		cy.get('.layer-list').should('be.empty');
		cy.contains('button', /^Undo$/).click();
		layers().should('have.length', 1);
		cy.screenshot('canvas-mobile');
		cy.document().then((doc) => expect(doc.documentElement.scrollWidth).to.be.at.most(390));
	});

	it('disables generation modes according to server configuration and rejects unsupported uploads', () => {
		generationEnabled = false;
		editEnabled = false;
		visit();
		draw();
		cy.get('#canvas-prompt').type('A sketch');
		cy.contains('button', 'Generate from text').should('be.disabled');
		cy.contains('button', 'Generate from canvas').should('be.disabled');
		cy.get('input[type=file]').selectFile(
			{
				contents: Cypress.Buffer.from('not an image'),
				fileName: 'test.txt',
				mimeType: 'text/plain'
			},
			{ force: true }
		);
		cy.get('[role=alert]').should('contain', 'Choose a PNG');
		layers().should('have.length', 1);
	});
});
