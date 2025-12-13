// Google Drive Picker API configuration
let API_KEY = '';
let CLIENT_ID = '';

// Function to fetch credentials from backend config
async function getCredentials() {
	const response = await fetch('/api/config');
	if (!response.ok) {
		throw new Error('Failed to fetch Google Drive credentials');
	}
	const config = await response.json();
	API_KEY = config.google_drive?.api_key;
	CLIENT_ID = config.google_drive?.client_id;

	if (!API_KEY || !CLIENT_ID) {
		throw new Error('Google Drive API credentials not configured');
	}
}
// Scope required for reading user-selected Drive files and their metadata
// drive.readonly: Read-only access to all files (sufficient for picker + sync)
// Note: drive.file is too restrictive (only files created by this app)
const SCOPE = ['https://www.googleapis.com/auth/drive.readonly'];

// Validate required credentials
const validateCredentials = () => {
	if (!API_KEY || !CLIENT_ID) {
		throw new Error('Google Drive API credentials not configured');
	}
	if (API_KEY === '' || CLIENT_ID === '') {
		throw new Error('Please configure valid Google Drive API credentials');
	}
};

let pickerApiLoaded = false;
let oauthToken: string | null = null;
let tokenExpiresAt: number | null = null; // Timestamp when token expires
let initialized = false;

// LocalStorage keys for token persistence
const STORAGE_KEY_TOKEN = 'google_drive_oauth_token';
const STORAGE_KEY_EXPIRES = 'google_drive_oauth_expires';

// Load token from localStorage on module initialization
const loadTokenFromStorage = () => {
	const storedToken = localStorage.getItem(STORAGE_KEY_TOKEN);
	const storedExpires = localStorage.getItem(STORAGE_KEY_EXPIRES);
	
	if (storedToken && storedExpires) {
		const expiresAt = parseInt(storedExpires, 10);
		const now = Date.now();
		const timeRemaining = Math.floor((expiresAt - now) / 1000);
		
		if (timeRemaining > 60) {
			oauthToken = storedToken;
			tokenExpiresAt = expiresAt;
			console.log(`[DRIVE AUTH] Loaded token from localStorage, expires in ${timeRemaining}s`);
			return true;
		} else {
			console.log(`[DRIVE AUTH] Stored token expired, clearing localStorage`);
			localStorage.removeItem(STORAGE_KEY_TOKEN);
			localStorage.removeItem(STORAGE_KEY_EXPIRES);
		}
	}
	return false;
};

// Save token to localStorage
const saveTokenToStorage = (token: string, expiresAt: number) => {
	localStorage.setItem(STORAGE_KEY_TOKEN, token);
	localStorage.setItem(STORAGE_KEY_EXPIRES, expiresAt.toString());
	console.log('[DRIVE AUTH] Token saved to localStorage');
};

// Clear token from localStorage
const clearTokenFromStorage = () => {
	localStorage.removeItem(STORAGE_KEY_TOKEN);
	localStorage.removeItem(STORAGE_KEY_EXPIRES);
	console.log('[DRIVE AUTH] Token cleared from localStorage');
};

export const loadGoogleDriveApi = () => {
	return new Promise((resolve, reject) => {
		if (typeof gapi === 'undefined') {
			const script = document.createElement('script');
			script.src = 'https://apis.google.com/js/api.js';
			script.onload = () => {
				gapi.load('picker', () => {
					pickerApiLoaded = true;
					resolve(true);
				});
			};
			script.onerror = reject;
			document.body.appendChild(script);
		} else {
			gapi.load('picker', () => {
				pickerApiLoaded = true;
				resolve(true);
			});
		}
	});
};

export const loadGoogleAuthApi = () => {
	return new Promise((resolve, reject) => {
		if (typeof google === 'undefined') {
			const script = document.createElement('script');
			script.src = 'https://accounts.google.com/gsi/client';
			script.onload = resolve;
			script.onerror = reject;
			document.body.appendChild(script);
		} else {
			resolve(true);
		}
	});
};

export const getAuthToken = async () => {
	// Try to load token from localStorage if not in memory
	if (!oauthToken || !tokenExpiresAt) {
		loadTokenFromStorage();
	}
	
	// Check if we have a valid cached token
	if (oauthToken && tokenExpiresAt) {
		const now = Date.now();
		const timeRemaining = Math.floor((tokenExpiresAt - now) / 1000);
		if (timeRemaining > 60) {
			console.log(`[DRIVE AUTH] Using cached token, expires in ${timeRemaining}s`);
			return oauthToken;
		} else {
			console.log(`[DRIVE AUTH] Cached token expired or expiring soon (${timeRemaining}s remaining), requesting new token`);
			oauthToken = null;
			tokenExpiresAt = null;
			clearTokenFromStorage();
		}
	}
	
	if (!oauthToken) {
		return new Promise((resolve, reject) => {
			const tokenClient = google.accounts.oauth2.initTokenClient({
				client_id: CLIENT_ID,
				scope: SCOPE.join(' '),
				callback: (response: any) => {
					if (response.access_token) {
						const token = response.access_token;
						oauthToken = token;
						
						// Capture expiration time from response
						const expiresIn = response.expires_in || 3600; // Default to 3600s if not provided
						tokenExpiresAt = Date.now() + (expiresIn * 1000);
						
						// Save to localStorage
						saveTokenToStorage(token, tokenExpiresAt);
						
						const expiresAtTime = new Date(tokenExpiresAt).toLocaleTimeString();
						console.log(`[DRIVE AUTH] New token obtained, expires_in: ${expiresIn}s (${Math.floor(expiresIn / 60)} minutes)`);
						console.log(`[DRIVE AUTH] Token will expire at: ${expiresAtTime}`);
						console.log(`[DRIVE AUTH] Full OAuth response:`, response);
						
						resolve(token);
					} else {
						reject(new Error('Failed to get access token'));
					}
				},
				error_callback: (error: any) => {
					reject(new Error(error.message || 'OAuth error occurred'));
				}
			});
			tokenClient.requestAccessToken();
		});
	}
	return oauthToken;
};

// Request a fresh auth token, bypassing cache
// Use this for sync operations where tokens may have expired
export const requestFreshAuthToken = async () => {
	await initialize();
	console.log('[DRIVE AUTH] Requesting fresh token for sync operation');
	return new Promise((resolve, reject) => {
		const tokenClient = google.accounts.oauth2.initTokenClient({
			client_id: CLIENT_ID,
			scope: SCOPE.join(' '),
			callback: (response: any) => {
				if (response.access_token) {
					const token = response.access_token;
					oauthToken = token;
					
					// Capture expiration time from response
					const expiresIn = response.expires_in || 3600; // Default to 3600s if not provided
					tokenExpiresAt = Date.now() + (expiresIn * 1000);
					
					// Save to localStorage only if token is not null
					if (token) {
						saveTokenToStorage(token, tokenExpiresAt);
					}
					
					const expiresAtTime = new Date(tokenExpiresAt).toLocaleTimeString();
					console.log(`[DRIVE AUTH] Fresh token obtained, expires_in: ${expiresIn}s (${Math.floor(expiresIn / 60)} minutes)`);
					console.log(`[DRIVE AUTH] Token will expire at: ${expiresAtTime}`);
					console.log(`[DRIVE AUTH] Full OAuth response:`, response);
					
					resolve(token);
				} else {
					reject(new Error('Failed to get access token'));
				}
			},
			error_callback: (error: any) => {
				reject(new Error(error.message || 'OAuth error occurred'));
			}
		});
		tokenClient.requestAccessToken();
	});
};

const initialize = async () => {
	if (!initialized) {
		await getCredentials();
		validateCredentials();
		await Promise.all([loadGoogleDriveApi(), loadGoogleAuthApi()]);
		initialized = true;
	}
};

// Fetch detailed metadata from Drive API
const fetchDriveFileMetadata = async (fileId: string, token: string, mimeType: string) => {
	try {
		console.log('[DRIVE] Calling Drive API for metadata:', {
			fileId,
			mimeType,
			hasToken: !!token,
			tokenPrefix: token ? token.substring(0, 10) + '...' : 'none'
		});
		
		// Google Workspace files (Docs/Sheets/Slides) don't have size or version in the same way
		// Use minimal fields that work for all file types
		const isWorkspaceFile = mimeType.includes('google-apps');
		const fields = isWorkspaceFile 
			? 'id,name,modifiedTime,mimeType,webViewLink'
			: 'id,name,modifiedTime,version,size,mimeType,webViewLink';
		
		console.log('[DRIVE] Fetching fields:', fields);
		
		const response = await fetch(
			`https://www.googleapis.com/drive/v3/files/${fileId}?fields=${fields}&supportsAllDrives=true`,
			{
				headers: {
					Authorization: `Bearer ${token}`,
					Accept: 'application/json'
				}
			}
		);

		console.log('[DRIVE] Drive API response:', {
			status: response.status,
			statusText: response.statusText,
			ok: response.ok
		});

		if (!response.ok) {
			const errorText = await response.text();
			console.error('[DRIVE] Drive API error:', {
				fileId,
				status: response.status,
				statusText: response.statusText,
				error: errorText
			});
			return null;
		}

		const metadata = await response.json();
		console.log('[DRIVE] Drive API metadata received:', metadata);
		return metadata;
	} catch (error) {
		console.error('[DRIVE] Exception fetching Drive file metadata:', error);
		return null;
	}
};

export const createPicker = () => {
	return new Promise(async (resolve, reject) => {
		try {
			console.log('Initializing Google Drive Picker...');
			await initialize();
			console.log('Getting auth token...');
			const token = await getAuthToken();
			if (!token) {
				console.error('Failed to get OAuth token');
				throw new Error('Unable to get OAuth token');
			}
			console.log('Auth token obtained successfully');

			const picker = new google.picker.PickerBuilder()
				.enableFeature(google.picker.Feature.NAV_HIDDEN)
				.enableFeature(google.picker.Feature.MULTISELECT_ENABLED)
				.addView(
					new google.picker.DocsView()
						.setIncludeFolders(false)
						.setSelectFolderEnabled(false)
						.setMimeTypes(
							'application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.google-apps.document,application/vnd.google-apps.spreadsheet,application/vnd.google-apps.presentation'
						)
				)
				.setOAuthToken(token)
				.setDeveloperKey(API_KEY)
				// Remove app ID setting as it's not needed and can cause 404 errors
				.setCallback(async (data: any) => {
					if (data[google.picker.Response.ACTION] === google.picker.Action.PICKED) {
						try {
							const docs = data[google.picker.Response.DOCUMENTS];
							console.log(`[DRIVE] Processing ${docs.length} selected file(s)`);
							
							const results = [];
							
							// Process each selected file
							for (const doc of docs) {
								console.log('[DRIVE] Processing document:', doc);
								
								const fileId = doc[google.picker.Document.ID];
								const fileName = doc[google.picker.Document.NAME];
								const fileUrl = doc[google.picker.Document.URL];

								if (!fileId || !fileName) {
									console.warn('[DRIVE] Skipping file with missing details:', doc);
									continue;
								}

								// Construct download URL based on MIME type
								const mimeType: string = doc[google.picker.Document.MIME_TYPE] || '';
								console.log('[DRIVE] File info:', {
									id: fileId,
									name: fileName,
									mimeType,
									url: fileUrl
								});

								let downloadUrl;
								let exportFormat;

								if (mimeType.includes('google-apps')) {
									// Handle Google Workspace files
									if (mimeType.includes('document')) {
										exportFormat = 'text/plain';
									} else if (mimeType.includes('spreadsheet')) {
										exportFormat = 'text/csv';
									} else if (mimeType.includes('presentation')) {
										exportFormat = 'text/plain';
									} else {
										exportFormat = 'application/pdf';
									}
									downloadUrl = `https://www.googleapis.com/drive/v3/files/${fileId}/export?mimeType=${encodeURIComponent(exportFormat)}`;
								} else {
									// Regular files use direct download URL
									downloadUrl = `https://www.googleapis.com/drive/v3/files/${fileId}?alt=media`;
								}
								
								// Download file
								const response = await fetch(downloadUrl, {
									headers: {
										Authorization: `Bearer ${token}`,
										Accept: '*/*'
									}
								});

								if (!response.ok) {
									const errorText = await response.text();
									console.error('[DRIVE] Download failed:', {
										file: fileName,
										status: response.status,
										error: errorText
									});
									continue; // Skip this file but continue with others
								}

								const blob = await response.blob();
								
								// Fetch Drive metadata for sync tracking
								console.log('[DRIVE] Fetching metadata for file:', fileId);
								const driveMetadata = await fetchDriveFileMetadata(fileId, token, mimeType as string);
								
								if (driveMetadata) {
									console.log('[DRIVE] Metadata fetched successfully:', {
										file_id: fileId,
										modified_time: driveMetadata.modifiedTime
									});
								} else {
									console.warn('[DRIVE] Failed to fetch metadata - file will not be syncable');
								}
								
								results.push({
									id: fileId,
									name: fileName,
									url: downloadUrl,
									blob: blob,
									headers: {
										Authorization: `Bearer ${token}`,
										Accept: '*/*'
									},
									// Include Drive metadata for storage
									driveMetadata: driveMetadata ? {
										file_id: fileId,
										modified_time: driveMetadata.modifiedTime,
										version: driveMetadata.version,
										web_view_link: driveMetadata.webViewLink,
										mime_type: driveMetadata.mimeType,
										size: driveMetadata.size
									} : null
								});
							}
							
							console.log(`[DRIVE] Successfully processed ${results.length} file(s)`);
							resolve(results); // Return array of files
						} catch (error) {
							reject(error);
						}
					} else if (data[google.picker.Response.ACTION] === google.picker.Action.CANCEL) {
						resolve(null);
					}
				})
				.build();
			picker.setVisible(true);
		} catch (error) {
			console.error('Google Drive Picker error:', error);
			reject(error);
		}
	});
};
