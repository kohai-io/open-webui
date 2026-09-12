/// <reference types="cypress" />
// Run against the local frontend preview. All API traffic is stubbed; no account is needed.
describe('Media phase one', () => {
	let records;
	let failPage;
	let failDelete;
	let pages;
	let welcome;
	const makeFile = (id, filename, content_type) => ({ id, filename, meta: { content_type } });

	beforeEach(() => {
		records = [
			makeFile('image', 'Landscape.png', 'image/png'),
			...Array.from({ length: 49 }, (_, i) => makeFile(`doc-${i}`, `Notes-${i}.txt`, 'text/plain')),
			makeFile('video', 'Clip.mp4', 'video/mp4'),
			makeFile('audio', 'Speech.mp3', 'audio/mpeg')
		];
		pages = [];
		failPage = false;
		failDelete = false;
		welcome = false;
		cy.intercept('**/api/**', (request) => {
			const url = new URL(request.url);
			const path = url.pathname;
			if (path === '/api/config')
				return request.reply({
					name: 'Open WebUI',
					version: '0.10.2',
					features: { enable_welcome_page: welcome, enable_websocket: false },
					audio: { stt: {}, tts: {} }
				});
			if (path === '/api/v1/auths/')
				return request.reply({
					id: 'media-test',
					name: 'Media Tester',
					email: 'media@example.test',
					role: 'user',
					permissions: { workspace: {}, chat: {} }
				});
			if (path === '/api/v1/users/user/settings')
				return request.reply({ ui: { showChangelog: false } });
			if (path === '/api/models') return request.reply({ data: [] });
			if (path === '/api/v1/files/' && request.method === 'GET') {
				const page = Number(url.searchParams.get('page'));
				pages.push(page);
				expect(url.searchParams.get('content')).to.equal('false');
				if (failPage) {
					failPage = false;
					return request.reply({ statusCode: 500, body: { detail: 'Test failure' } });
				}
				return request.reply({
					items: records.slice((page - 1) * 50, page * 50),
					total: records.length
				});
			}
			if (path.startsWith('/api/v1/files/') && request.method === 'DELETE') {
				if (failDelete) return request.reply({ statusCode: 403, body: { detail: 'Test denial' } });
				records = records.filter((file) => file.id !== path.split('/').pop());
				return request.reply({ message: 'File deleted successfully' });
			}
			if (path.endsWith('/content'))
				return request.reply({
					headers: { 'content-type': 'image/svg+xml' },
					body: '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="240"><rect width="400" height="240" fill="#a5b4fc"/></svg>'
				});
			request.reply([]);
		});
	});

	const visit = () =>
		cy.visit('/media', {
			onBeforeLoad(window) {
				window.localStorage.setItem('token', 'media-test-token');
				window.localStorage.setItem('locale', 'en-US');
				window.localStorage.setItem('sidebar', 'true');
			}
		});

	it('loads one page at a time, filters loaded media and closes its preview', () => {
		cy.viewport(1280, 720);
		visit();
		cy.get('article').should('have.length', 1);
		cy.then(() => expect(pages).to.deep.equal([1]));
		cy.get('a[href="/welcome"]').should('not.exist');
		cy.get('a[href="/media"]:visible').should('exist');
		cy.get('button[aria-label="Preview: Landscape.png"]').click();
		cy.get('[role="dialog"]').should('be.visible');
		cy.get('[role="dialog"]').contains('button', 'Close').click();
		cy.get('[role="dialog"]').should('not.exist');
		cy.contains('button', 'Load more').click();
		cy.get('article').should('have.length', 3);
		cy.screenshot('media-desktop');
		cy.get('#sidebar button[aria-label="Close Sidebar"]').click();
		cy.get('a[href="/media"]:visible').click();
		cy.get('article').should('have.length', 3);
		cy.get('select[aria-label="Type"]').select('audio');
		cy.get('article').should('have.length', 1).and('contain', 'Speech.mp3');
		cy.get('select[aria-label="Type"]').select('all');
		cy.get('input[type="search"]').type('clip');
		cy.get('article').should('have.length', 1).and('contain', 'Clip.mp4');
		cy.get('article a').should('have.attr', 'href').and('include', 'attachment=true');
	});

	it('keeps pagination usable after a non-media page and a failed request', () => {
		records[0] = makeFile('doc-first', 'First.txt', 'text/plain');
		visit();
		cy.contains('No matching media in the files loaded so far.').should('be.visible');
		cy.then(() => {
			failPage = true;
		});
		cy.contains('button', 'Load more').click();
		cy.get('[role="alert"]').should('be.visible');
		cy.contains('button', 'Retry').click();
		cy.get('article').should('have.length', 2);
		cy.then(() => expect(pages).to.deep.equal([1, 2, 2]));
	});

	it('confirms deletion, preserves a denied file, and restarts pagination after success', () => {
		visit();
		cy.get('article').contains('button', 'Delete').click();
		cy.contains('button', 'Cancel').click();
		cy.then(() => {
			expect(records).to.have.length(52);
			failDelete = true;
		});
		cy.get('article').contains('button', 'Delete').click();
		cy.get('button')
			.filter((_, button) => button.textContent.trim() === 'Delete')
			.last()
			.click();
		cy.contains('Error deleting file').should('be.visible');
		cy.get('article').should('contain', 'Landscape.png');
		cy.then(() => {
			failDelete = false;
		});
		cy.get('article').contains('button', 'Delete').click();
		cy.get('button')
			.filter((_, button) => button.textContent.trim() === 'Delete')
			.last()
			.click();
		cy.get('article').should('not.contain', 'Landscape.png').and('contain', 'Clip.mp4');
		cy.then(() => expect(pages).to.deep.equal([1, 1]));
		cy.contains('button', 'Load more').click();
		cy.get('article').should('have.length', 2);
	});

	it('opens and closes the mobile sidebar with Welcome enabled', () => {
		welcome = true;
		cy.viewport(390, 844);
		visit();
		cy.get('header button[aria-label="Open Sidebar"]').click();
		cy.get('#sidebar a[href="/media"]').click();
		cy.get('header button[aria-label="Open Sidebar"]').click();
		cy.get('#sidebar a[href="/welcome"]').should('be.visible');
		cy.get('#sidebar a[href="/media"]').click();
		cy.get('header button[aria-label="Open Sidebar"]').should('be.visible');
		cy.get('#sidebar').should('not.exist');
		cy.get('article').should('be.visible');
		cy.screenshot('media-mobile');
	});
});
