import { describe, expect, it } from 'vitest';
import { buildWelcomeChatQuery, classifyWelcomeCatalogue, orderWelcomeAgents } from './catalogue';

describe('classifyWelcomeCatalogue', () => {
	it('intersects OWUI workspace agents and functions with executable models', () => {
		const result = classifyWelcomeCatalogue(
			[
				{ id: 'base', name: 'Base' },
				{ id: 'assistant', name: 'Unmerged name' },
				{ id: 'pipe', name: 'Pipe' }
			],
			[
				{
					id: 'assistant',
					name: 'Research agent',
					base_model_id: 'base',
					is_active: true,
					meta: { tags: [{ name: 'research' }] }
				},
				{ id: 'hidden', name: 'Hidden', base_model_id: 'base', is_active: true }
			],
			[{ id: 'pipe', is_active: true }]
		);

		expect(result.agents).toEqual([
			{ id: 'assistant', name: 'Research agent', tags: ['research'], kind: 'agent' },
			{ id: 'pipe', name: 'Pipe', tags: [], kind: 'agent' }
		]);
		expect(result.models.map((item) => item.id)).toEqual(['base']);
		expect(result.agents.some((item) => item.id === 'hidden')).toBe(false);
	});

	it('does not classify inactive workspace records or functions as agents', () => {
		const result = classifyWelcomeCatalogue(
			[{ id: 'inactive', name: 'Inactive' }],
			[{ id: 'inactive', name: 'Inactive', base_model_id: 'base', is_active: false }],
			[{ id: 'inactive', is_active: false }]
		);
		expect(result.agents).toEqual([]);
		expect(result.models).toHaveLength(1);
	});
});

describe('Welcome preferences and handoff', () => {
	it('preserves stored order and appends newly available agents', () => {
		expect(
			orderWelcomeAgents(
				[{ id: 'new' }, { id: 'second' }, { id: 'first' }],
				['first', 'missing', 'second']
			).map((item) => item.id)
		).toEqual(['first', 'second', 'new']);
	});

	it('hands composer capabilities to the native chat route', () => {
		expect(
			buildWelcomeChatQuery({
				message: '  explain this  ',
				webSearchEnabled: true,
				imageGenerationEnabled: true,
				codeInterpreterEnabled: true,
				selectedToolIds: ['tool-a', 'tool-b']
			})
		).toBe(
			'q=explain+this&web-search=true&image-generation=true&code-interpreter=true&tools=tool-a%2Ctool-b'
		);
	});
});
