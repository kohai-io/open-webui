/// <reference types="cypress" />
// Native composer integration: all API traffic is stubbed, including uploads and model calls.
describe('Welcome native composer', () => {
	let welcome;
	let landingPageMode;
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
		cy.intercept('**/api/**', (request) => {
			const path = new URL(request.url).pathname;
			if (path === '/api/config')
				return request.reply({
					name: 'Open WebUI',
					version: '0.11.3',
					default_models: 'model-a',
					features: { enable_welcome_page: welcome, enable_websocket: false },
					audio: { stt: {}, tts: {} },
					file: { max_count: 10 }
				});
			if (path === '/api/v1/auths/')
				return request.reply({
					id: 'welcome-test',
					name: 'Welcome Tester',
					email: 'welcome@example.test',
					role: 'admin',
					permissions: { workspace: {}, chat: {} }
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

	it('places one composer below the greeting on mobile and keeps New Chat separate', () => {
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
		cy.screenshot('welcome-native-mobile');
		cy.contains('a:visible', 'New Chat').click();
		cy.location('pathname').should('equal', '/');
		cy.contains('h1', 'Hello, Welcome Tester').should('not.exist');
		cy.get('#chat-input').should('be.visible');
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
});
