import type { i18n } from 'i18next';

// Keep feature-owned descriptions out of the upstream translation catalogue.
const copy = {
	searchDescription: 'Find past chats',
	notesDescription: 'Capture ideas',
	mediaDescription: 'Browse your media'
};

export function welcomeText(i18n: i18n, key: keyof typeof copy): string {
	return i18n.t(key, { ns: 'customWelcome', defaultValue: copy[key] });
}
