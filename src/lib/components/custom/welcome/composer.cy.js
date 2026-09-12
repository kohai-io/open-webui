/// <reference types="cypress" />
// Native composer integration: all API traffic is stubbed, including uploads and model calls.
describe('Welcome native composer', () => {
	let welcome;
	let landingPageMode;
	let notesEnabled;
	let role;
	let notesAllowed;
	const model = (id, name) => ({
		id,
		name,
		owned_by: 'openai',
		info: { id, name, meta: { capabilities: { vision: true, file_upload: true } } }
	});
	const models = [
		model('model-a', 'Model Alpha'),
		model('model-b', 'Model Beta'),
		model('agent', 'Research Agent')
	];
	const file = {
		id: 'welcome-file',
		filename: 'welcome.txt',
		meta: { name: 'welcome.txt', content_type: 'text/plain', size: 14 },
		data: { status: 'completed' }
	};

	beforeEach(() => {
		welcome = true;
		landingPageMode = 'chat';
		notesEnabled = true;
		role = 'admin';
		notesAllowed = true;
		cy.intercept('**/api/**', (request) => {
			const path = new URL(request.url).pathname;
			if (path === '/api/config')
				return request.reply({
					name: 'Open WebUI',
					version: '0.11.3',
					default_models: 'model-a',
					features: {
						enable_welcome_page: welcome,
						enable_notes: notesEnabled,
						enable_websocket: false
					},
					audio: { stt: {}, tts: {} },
					file: { max_count: 10 }
				});
			if (path === '/api/v1/auths/')
				return request.reply({
					id: 'welcome-test',
					name: 'Welcome Tester',
					email: 'welcome@example.test',
					role,
					permissions: { workspace: {}, chat: {}, features: { notes: notesAllowed } }
				});
			if (path === '/api/v1/users/user/settings')
				return request.reply({
					ui: {
						models: ['model-a'],
						showChangelog: false,
						landingPageMode,
						streamResponse: false,
						title: { auto: false },
						autoTags: false,
						autoFollowUps: false
					}
				});
			if (path === '/api/models') return request.reply({ data: models });
			if (
				path === '/api/v1/notes/' ||
				path === '/api/v1/notes/search' ||
				(path === '/api/v1/files/' && request.method === 'GET')
			)
				return request.reply({ items: [], total: 0 });
			if (path === '/api/v1/models/list')
				return request.reply({
					items: [
						{ id: 'agent', name: 'Research Agent', base_model_id: 'model-a', is_active: true }
					],
					total: 1
				});
			if (path === '/api/chat/completions') {
				request.alias = 'completion';
				return request.reply({ chat_id: 'welcome-chat', task_id: 'fixture-task' });
			}
			if (path === '/api/v1/files/' && request.method === 'POST') {
				request.alias = 'upload';
				return request.reply(file);
			}
			if (path === '/api/v1/files/welcome-file/process/status')
				return request.reply({
					headers: { 'content-type': 'text/event-stream' },
					body: 'data: {"status":"completed"}\n\ndata: [DONE]\n\n'
				});
			request.reply([]);
		});
	});

	const visit = (path = '/welcome') =>
		cy.visit(path, {
			onBeforeLoad(window) {
				window.localStorage.clear();
				window.sessionStorage.clear();
				window.localStorage.setItem('token', 'welcome-test-token');
				window.localStorage.setItem('locale', 'en-US');
				window.localStorage.setItem('sidebar', 'true');
			}
		});
	const attachFile = () => {
		cy.get('input[type="file"]')
			.first()
			.selectFile(
				{
					contents: Cypress.Buffer.from('Welcome sample'),
					fileName: 'welcome.txt',
					mimeType: 'text/plain'
				},
				{ force: true }
			);
		cy.wait('@upload');
		cy.contains('welcome.txt').should('be.visible');
	};

	it('uses the selected native model and transitions from Welcome to a chat', () => {
		cy.viewport(1280, 720);
		visit();
		cy.contains('h1', 'Hello, Welcome Tester').should('be.visible');
		cy.get('#chat-input').should('have.length', 1).and('be.visible');
		cy.contains('button', 'Model Alpha').click();
		cy.get('#model-search-input').type('Model Beta');
		cy.contains('button', 'Model Beta').click();
		cy.get('#chat-input').type('Please explain this');
		cy.get('#send-message-button').click();
		cy.wait('@completion').then(({ request }) => {
			expect(request.body.model).to.equal('model-b');
			expect(request.body.user_message.content).to.equal('Please explain this');
		});
		cy.location('pathname').should('equal', '/c/welcome-chat');
		cy.contains('h1', 'Hello, Welcome Tester').should('not.exist');
		cy.get('#chat-input').should('have.length', 1);
		cy.get('#sidebar a[href="/welcome"]').click();
		cy.contains('h1', 'Hello, Welcome Tester').should('be.visible');
	});

	it('sends a native attachment with the first message', () => {
		visit();
		cy.get('#chat-input').should('be.visible');
		attachFile();
		cy.get('#chat-input').type('Read this file');
		cy.get('#send-message-button').click();
		cy.wait('@completion').then(({ request }) => {
			expect(request.body.user_message.files).to.have.length(1);
			expect(request.body.user_message.files[0].id).to.equal('welcome-file');
			expect(request.body.files.map(({ id }) => id)).to.include('welcome-file');
		});
	});

	it('keeps attachments when opening an agent from Welcome', () => {
		visit();
		cy.get('#chat-input').should('be.visible');
		attachFile();
		cy.get('[data-agent-index]').filter(':visible').contains('Research Agent').click();
		cy.location('search').should('equal', '?models=agent');
		cy.contains('welcome.txt').should('be.visible');
		cy.get('#chat-input').type('Help with this file');
		cy.get('#send-message-button').click();
		cy.wait('@completion').then(({ request }) => {
			expect(request.body.model).to.equal('agent');
			expect(request.body.user_message.files[0].id).to.equal('welcome-file');
		});
	});

	it('anchors one composer at the bottom on mobile and keeps New Chat separate', () => {
		cy.viewport(390, 844);
		visit();
		cy.contains('h1', 'Hello, Welcome Tester')
			.should('be.visible')
			.then(($heading) => {
				cy.get('#chat-input')
					.should('have.length', 1)
					.and('be.visible')
					.then(($input) => {
						expect($input[0].getBoundingClientRect().top).to.be.greaterThan(
							$heading[0].getBoundingClientRect().bottom
						);
					});
			});
		cy.contains('button', 'Model Alpha').should('be.visible');
		cy.get('[data-testid="welcome-composer"]').should(($composer) => {
			expect($composer[0].getBoundingClientRect().bottom).to.be.closeTo(844, 2);
		});
		cy.contains('button', 'Model Alpha').click();
		cy.get('#model-search-input').should('be.visible').type('Model Beta');
		cy.contains('button', 'Model Beta').click();
		cy.contains('button', 'Model Beta').should('be.visible');
		cy.screenshot('welcome-native-mobile');
		cy.get('nav button').first().click();
		cy.get('#sidebar a[aria-label="New Chat"]').click();
		cy.location('pathname').should('equal', '/');
		cy.contains('h1', 'Hello, Welcome Tester').should('not.exist');
		cy.get('#chat-input').should('be.visible');
	});

	it('keeps the composer visible on a short screen and preserves drafts across breakpoints', () => {
		cy.viewport(390, 420);
		visit();
		cy.get('#chat-input').type('Keep this draft');
		attachFile();
		cy.get('[data-testid="welcome-content"]').scrollTo('bottom');
		cy.get('[data-testid="welcome-composer"]').should(($composer) => {
			expect($composer[0].getBoundingClientRect().bottom).to.be.closeTo(420, 2);
		});
		cy.get('#chat-input').should('be.visible').and('contain.text', 'Keep this draft');
		cy.screenshot('welcome-native-mobile-short');
		cy.viewport(1280, 720);
		cy.get('#chat-input').should('have.length', 1).and('contain.text', 'Keep this draft');
		cy.contains('welcome.txt').should('be.visible');
		cy.contains('h1', 'Hello, Welcome Tester').then(($heading) => {
			cy.get('[data-testid="welcome-composer"]').should(($composer) => {
				const rect = $composer[0].getBoundingClientRect();
				expect(rect.top).to.be.greaterThan($heading[0].getBoundingClientRect().bottom);
				expect(rect.top).to.be.lessThan(360);
			});
		});
		cy.screenshot('welcome-native-desktop');
		cy.viewport(390, 844);
		cy.get('#chat-input').should('have.length', 1).and('contain.text', 'Keep this draft');
		cy.contains('welcome.txt').should('be.visible');
		cy.get('[data-testid="welcome-composer"]').should(($composer) => {
			expect($composer[0].getBoundingClientRect().bottom).to.be.closeTo(844, 2);
		});
	});

	it('redirects Welcome to ordinary Chat when the feature is disabled', () => {
		welcome = false;
		visit();
		cy.location('pathname').should('equal', '/');
		cy.get('#chat-input').should('be.visible');
		cy.get('a[href="/welcome"]').should('not.exist');
	});

	it('keeps the default New Chat landing composer working', () => {
		landingPageMode = '';
		visit('/');
		cy.contains('h1', 'Hello, Welcome Tester').should('not.exist');
		cy.get('#chat-input').should('have.length', 1).and('be.visible').type('Start from New Chat');
		cy.contains('button', 'Model Alpha').should('be.visible');
		cy.get('#send-message-button').click();
		cy.wait('@completion').then(({ request }) => {
			expect(request.body.model).to.equal('model-a');
			expect(request.body.user_message.content).to.equal('Start from New Chat');
		});
	});

	for (const [device, width, height] of [
		['desktop', 1280, 900],
		['mobile', 390, 700]
	]) {
		it(`opens Search, Notes and Media from the same Quick Actions on ${device}`, () => {
			cy.viewport(width, height);
			visit();
			cy.get('#chat-input').type('Keep my draft');
			cy.get('section[aria-labelledby="welcome-quick-actions-title"]')
				.as('quickActions')
				.should('have.length', 1);
			cy.get('@quickActions')
				.find('button, a')
				.should(($actions) => {
					expect([...$actions].map((action) => action.getAttribute('aria-label'))).to.deep.equal([
						'Search',
						'Notes',
						'Media'
					]);
					for (const action of $actions) {
						const rect = action.getBoundingClientRect();
						expect(rect.width).to.be.greaterThan(44);
						expect(rect.height).to.be.greaterThan(44);
						expect(rect.left).to.be.at.least(0);
						expect(rect.right).to.be.at.most(width);
					}
				});
			cy.screenshot(`welcome-quick-actions-${device}`);
			cy.get('@quickActions').find('button[aria-label="Search"]').click();
			cy.get('input[placeholder="Search"]:visible')
				.should('be.focused')
				.type('saved chat')
				.type('{esc}');
			cy.get('input[placeholder="Search"]:visible').should('not.exist');
			cy.get('#chat-input').should('contain.text', 'Keep my draft');
			cy.get('@quickActions').find('a[aria-label="Notes"]').click();
			cy.location('pathname').should('equal', '/notes');
			cy.go('back');
			cy.get(
				'section[aria-labelledby="welcome-quick-actions-title"] a[aria-label="Media"]'
			).click();
			cy.location('pathname').should('equal', '/media');
			cy.contains('h1', 'Media').should('be.visible');
		});
	}

	for (const restriction of ['disabled', 'not permitted']) {
		it(`hides the Notes quick action when Notes is ${restriction}`, () => {
			role = 'user';
			notesEnabled = restriction !== 'disabled';
			notesAllowed = restriction !== 'not permitted';
			visit();
			cy.get('section[aria-labelledby="welcome-quick-actions-title"]')
				.find('button, a')
				.should(($actions) => {
					expect([...$actions].map((action) => action.getAttribute('aria-label'))).to.deep.equal([
						'Search',
						'Media'
					]);
				});
		});
	}
});
