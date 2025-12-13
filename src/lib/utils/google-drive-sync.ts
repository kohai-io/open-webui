import { getAuthToken } from './google-drive-picker';

export interface DriveFileMetadata {
	id: string;
	name: string;
	modifiedTime: string;
	version?: string;
	size?: number;
	mimeType: string;
	webViewLink?: string;
}

export interface DriveFileSyncStatus {
	file_id: string;
	has_update: boolean;
	current_modified_time?: string;
	stored_modified_time?: string;
	error?: string;
}

const getExportFormat = (mimeType: string): string => {
	if (mimeType.includes('document')) {
		return 'text/plain';
	} else if (mimeType.includes('spreadsheet')) {
		return 'text/csv';
	} else if (mimeType.includes('presentation')) {
		return 'text/plain';
	} else {
		return 'application/pdf';
	}
};

export const fetchDriveFileMetadata = async (
	fileId: string,
	token?: string
): Promise<DriveFileMetadata | null> => {
	try {
		const authToken = token || (await getAuthToken());
		if (!authToken) {
			throw new Error('Failed to get OAuth token');
		}

		const response = await fetch(
			`https://www.googleapis.com/drive/v3/files/${fileId}?fields=id,name,modifiedTime,version,size,mimeType,webViewLink`,
			{
				headers: {
					Authorization: `Bearer ${authToken}`,
					Accept: 'application/json'
				}
			}
		);

		if (!response.ok) {
			const error = await response.json().catch(() => ({}));
			console.error(`Failed to fetch Drive metadata for ${fileId}:`, error);
			return null;
		}

		return await response.json();
	} catch (error) {
		console.error('Error fetching Drive file metadata:', error);
		return null;
	}
};

export const checkDriveFileUpdated = async (
	fileId: string,
	lastModifiedTime: string,
	token?: string
): Promise<boolean> => {
	const metadata = await fetchDriveFileMetadata(fileId, token);
	if (!metadata) {
		return false;
	}

	const currentModified = new Date(metadata.modifiedTime);
	const storedModified = new Date(lastModifiedTime);

	return currentModified > storedModified;
};

export const downloadDriveFile = async (
	fileId: string,
	mimeType: string,
	token?: string
): Promise<Blob | null> => {
	try {
		const authToken = token || (await getAuthToken());
		if (!authToken) {
			throw new Error('Failed to get OAuth token');
		}

		let downloadUrl: string;

		if (mimeType.includes('google-apps')) {
			const exportFormat = getExportFormat(mimeType);
			downloadUrl = `https://www.googleapis.com/drive/v3/files/${fileId}/export?mimeType=${encodeURIComponent(exportFormat)}`;
		} else {
			downloadUrl = `https://www.googleapis.com/drive/v3/files/${fileId}?alt=media`;
		}

		const response = await fetch(downloadUrl, {
			headers: {
				Authorization: `Bearer ${authToken}`,
				Accept: '*/*'
			}
		});

		if (!response.ok) {
			const errorText = await response.text();
			console.error('Download failed:', {
				status: response.status,
				statusText: response.statusText,
				error: errorText
			});
			throw new Error(`Failed to download file (${response.status}): ${errorText}`);
		}

		return await response.blob();
	} catch (error) {
		console.error('Error downloading Drive file:', error);
		return null;
	}
};

export const checkMultipleFilesForUpdates = async (
	files: Array<{ fileId: string; lastModifiedTime: string }>,
	token?: string
): Promise<DriveFileSyncStatus[]> => {
	const results: DriveFileSyncStatus[] = [];

	for (const file of files) {
		try {
			const metadata = await fetchDriveFileMetadata(file.fileId, token);

			if (!metadata) {
				results.push({
					file_id: file.fileId,
					has_update: false,
					error: 'Failed to fetch metadata'
				});
				continue;
			}

			const currentModified = new Date(metadata.modifiedTime);
			const storedModified = new Date(file.lastModifiedTime);
			const hasUpdate = currentModified > storedModified;

			results.push({
				file_id: file.fileId,
				has_update: hasUpdate,
				current_modified_time: metadata.modifiedTime,
				stored_modified_time: file.lastModifiedTime
			});
		} catch (error) {
			results.push({
				file_id: file.fileId,
				has_update: false,
				error: error instanceof Error ? error.message : 'Unknown error'
			});
		}
	}

	return results;
};
