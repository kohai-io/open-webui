/// <reference types="cypress" />
// Run against a disposable instance with an existing test account; see PATCHES.md.
describe('Welcome routing', () => {
	const login = (path = '/auth') => {
		cy.visit(path, {
			onBeforeLoad(window) {
				window.localStorage.setItem('sidebar', 'true');
				window.localStorage.setItem('locale', 'en-US');
			}
		});
		cy.get('input[type="email"]').type(Cypress.env('WELCOME_TEST_EMAIL'));
		cy.get('input[type="password"]').type(Cypress.env('WELCOME_TEST_PASSWORD'), { log: false });
		cy.get('button[type="submit"]').click();
	};

	/** @param {boolean} enabled */
	const configureWelcome = (enabled) => {
		cy.intercept('GET', '/api/config', (request) => {
			request.continue((response) => {
				response.body.features.enable_welcome_page = enabled;
			});
		});
	};

	before(() => {
		expect(Cypress.env('WELCOME_TEST_EMAIL'), 'test account email').to.be.a('string').and.not.be
			.empty;
		expect(Cypress.env('WELCOME_TEST_PASSWORD'), 'test account password').to.be.a('string').and.not
			.be.empty;
	});

	beforeEach(() => {
		configureWelcome(true);
		cy.intercept('GET', '/api/v1/users/user/settings', {
			ui: { showChangelog: false }
		});
	});

	it('uses Welcome after sign-in without a destination', () => {
		login();
		cy.location('pathname').should('eq', '/welcome');
		cy.get('#chat-input').should('be.visible');
	});

	it('preserves an explicit root sign-in destination', () => {
		login('/auth?redirect=%2F');
		cy.location('pathname').should('eq', '/');
		cy.get('#chat-input').should('be.visible');
	});

	it('preserves a prompt and query parameters through sign-in', () => {
		login('/auth?redirect=%2F%3Fq%3Droute-check%26submit%3Dfalse');
		cy.location('search').should('eq', '?q=route-check&submit=false');
		cy.get('#chat-input').should('contain.text', 'route-check');
	});

	it('keeps direct root visits on Chat', () => {
		login();
		cy.location('pathname').should('eq', '/welcome');
		cy.visit('/');
		cy.get('#chat-input').should('be.visible');
		cy.visit('/?utm_source=route-check');
		cy.get('#chat-input').should('be.visible');
	});

	it('navigates between Home and New Chat in both desktop sidebar states', () => {
		cy.viewport(1440, 1050);
		login();
		cy.location('pathname').should('eq', '/welcome');
		cy.get('#sidebar a[aria-label="New Chat"]').click();
		cy.location('pathname').should('eq', '/');
		cy.get('#chat-input').should('be.visible');
		cy.window().then((window) => {
			window.document.documentElement.dataset.welcomeNavigationMarker = 'true';
		});
		cy.get('#sidebar a[href="/welcome"]').click();
		cy.location('pathname').should('eq', '/welcome');
		cy.document().its('documentElement.dataset.welcomeNavigationMarker').should('eq', 'true');
		cy.get('#sidebar button[aria-label="Close Sidebar"]').click();
		cy.get('a[aria-label="New Chat"]:visible').click();
		cy.get('#chat-input').should('be.visible');
		cy.get('a[href="/welcome"]:visible').click();
		cy.location('pathname').should('eq', '/welcome');
	});

	it('navigates between Home and New Chat on mobile', () => {
		cy.viewport(390, 844);
		login();
		cy.location('pathname').should('eq', '/welcome');
		cy.get('[data-sonner-toast]', { timeout: 10000 }).should('not.exist');
		cy.get('nav button').first().click();
		cy.get('#sidebar a[aria-label="New Chat"]').click();
		cy.get('#chat-input').should('be.visible');
		cy.get('nav button').first().click();
		cy.get('#sidebar a[href="/welcome"]').click();
		cy.location('pathname').should('eq', '/welcome');
		cy.get('#chat-input').should('be.visible');
	});

	it('falls back to Chat and hides Home when Welcome is disabled', () => {
		configureWelcome(false);
		login();
		cy.location('pathname').should('eq', '/');
		cy.get('#chat-input').should('be.visible');
		cy.visit('/welcome');
		cy.location('pathname').should('eq', '/');
		cy.get('#chat-input').should('be.visible');
		cy.get('a[href="/welcome"]').should('not.exist');
	});
});
