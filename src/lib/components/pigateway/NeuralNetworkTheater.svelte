<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { chats, chatId, models } from '$lib/stores';
	import { getChatList, createNewChat, updateChatById, getPinnedChatList, getChatById, getChatsByFolderId } from '$lib/apis/chats';
	import { getFolders, getFolderById } from '$lib/apis/folders';
	import { goto } from '$app/navigation';
	import { MediaPipeGestureController, type GestureType, type DualGestureType, type AllGestureTypes } from '$lib/utils/mediapipe-gesture';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	
	export let onClose: () => void;
	
	// Mobile detection and touch controls
	let isMobile = false;
	let showMobileControls = false;
	let touchStartPos = { x: 0, y: 0 };
	let joystickActive = false;
	let joystickDelta = { x: 0, y: 0 };
	let joystickCenter = { x: 0, y: 0 };
	let mobileMenuOpen = false;
	
	// Check for mobile on mount
	const checkMobile = () => {
		isMobile = window.innerWidth <= 768 || 'ontouchstart' in window;
		showMobileControls = isMobile;
	};
	
	// Virtual joystick handlers
	const handleJoystickStart = (e: TouchEvent) => {
		e.preventDefault();
		const touch = e.touches[0];
		const rect = (e.target as HTMLElement).getBoundingClientRect();
		joystickCenter = { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
		joystickActive = true;
		joystickDelta = { x: 0, y: 0 };
	};
	
	const handleJoystickMove = (e: TouchEvent) => {
		if (!joystickActive) return;
		e.preventDefault();
		const touch = e.touches[0];
		const maxDist = 40;
		let dx = touch.clientX - joystickCenter.x;
		let dy = touch.clientY - joystickCenter.y;
		const dist = Math.sqrt(dx * dx + dy * dy);
		if (dist > maxDist) {
			dx = (dx / dist) * maxDist;
			dy = (dy / dist) * maxDist;
		}
		joystickDelta = { x: dx / maxDist, y: dy / maxDist };
	};
	
	const handleJoystickEnd = () => {
		joystickActive = false;
		joystickDelta = { x: 0, y: 0 };
	};
	
	// Apply joystick movement in animation loop
	const applyJoystickMovement = () => {
		if (!joystickActive) return;
		const moveSpeed = 1.5;
		cameraTarget.x += joystickDelta.x * moveSpeed;
		cameraTarget.z += joystickDelta.y * moveSpeed;
	};
	
	// Chat data for visualization
	let userChats: any[] = [];
	let chatBuildings: Map<string, any> = new Map(); // chatId -> building mesh
	let hoveredChat: any = null;
	let selectedChatBuilding: any = null;
	
	// Folder data for visualization
	let folders: Map<string, any> = new Map(); // folderId -> folder data
	let folderNodes: Map<string, any> = new Map(); // folderId -> folder 3D node
	let folderConnections: any[] = []; // Lines connecting folders to their chats
	
	// Cyberspace Chat Interface
	let cyberspaceChat = {
		active: false,
		modelId: '',      // Model ID for API calls
		displayName: '',  // Friendly name for display
		chatId: '',       // Persistent chat ID in database
		messages: [] as { role: 'user' | 'assistant'; content: string; id?: string }[],
		inputText: '',
		isLoading: false
	};
	let chatInputRef: HTMLInputElement;
	
	// Chat window position (draggable) and size (resizable)
	let chatWindowPos = { x: 0, y: 0 }; // 0,0 means use default CSS position
	let chatWindowSize = { width: 400, height: 500 }; // Default size
	let isDraggingChat = false;
	let isResizingChat = false;
	let resizeDirection = ''; // 'se', 'sw', 'ne', 'nw', 'e', 'w', 'n', 's'
	let dragOffset = { x: 0, y: 0 };
	let resizeStart = { x: 0, y: 0, width: 0, height: 0, posX: 0, posY: 0 };
	
	const startChatDrag = (e: MouseEvent) => {
		if (isResizingChat) return;
		isDraggingChat = true;
		const chatEl = (e.target as HTMLElement).closest('.cyberspace-chat') as HTMLElement;
		if (chatEl) {
			const rect = chatEl.getBoundingClientRect();
			dragOffset.x = e.clientX - rect.left;
			dragOffset.y = e.clientY - rect.top;
			// Initialize position if not set
			if (chatWindowPos.x === 0 && chatWindowPos.y === 0) {
				chatWindowPos.x = rect.left;
				chatWindowPos.y = rect.top;
			}
		}
		e.preventDefault();
	};
	
	const startChatResize = (e: MouseEvent, direction: string) => {
		isResizingChat = true;
		resizeDirection = direction;
		const chatEl = (e.target as HTMLElement).closest('.cyberspace-chat') as HTMLElement;
		if (chatEl) {
			const rect = chatEl.getBoundingClientRect();
			resizeStart = {
				x: e.clientX,
				y: e.clientY,
				width: rect.width,
				height: rect.height,
				posX: chatWindowPos.x || rect.left,
				posY: chatWindowPos.y || rect.top
			};
			// Initialize position if not set
			if (chatWindowPos.x === 0 && chatWindowPos.y === 0) {
				chatWindowPos.x = rect.left;
				chatWindowPos.y = rect.top;
			}
		}
		e.preventDefault();
		e.stopPropagation();
	};
	
	const onChatDrag = (e: MouseEvent) => {
		if (isDraggingChat) {
			chatWindowPos.x = Math.max(0, Math.min(window.innerWidth - chatWindowSize.width, e.clientX - dragOffset.x));
			chatWindowPos.y = Math.max(0, Math.min(window.innerHeight - 100, e.clientY - dragOffset.y));
		} else if (isResizingChat) {
			const dx = e.clientX - resizeStart.x;
			const dy = e.clientY - resizeStart.y;
			const minWidth = 300;
			const minHeight = 300;
			const maxWidth = window.innerWidth - 50;
			const maxHeight = window.innerHeight - 50;
			
			// Handle different resize directions
			if (resizeDirection.includes('e')) {
				chatWindowSize.width = Math.max(minWidth, Math.min(maxWidth, resizeStart.width + dx));
			}
			if (resizeDirection.includes('w')) {
				const newWidth = Math.max(minWidth, Math.min(maxWidth, resizeStart.width - dx));
				const widthDiff = resizeStart.width - newWidth;
				chatWindowPos.x = resizeStart.posX + widthDiff;
				chatWindowSize.width = newWidth;
			}
			if (resizeDirection.includes('s')) {
				chatWindowSize.height = Math.max(minHeight, Math.min(maxHeight, resizeStart.height + dy));
			}
			if (resizeDirection.includes('n')) {
				const newHeight = Math.max(minHeight, Math.min(maxHeight, resizeStart.height - dy));
				const heightDiff = resizeStart.height - newHeight;
				chatWindowPos.y = resizeStart.posY + heightDiff;
				chatWindowSize.height = newHeight;
			}
		}
	};
	
	const stopChatDrag = () => {
		isDraggingChat = false;
		isResizingChat = false;
		resizeDirection = '';
	};
	
	let container: HTMLDivElement;
	let sceneCanvas: HTMLCanvasElement;
	let videoElement: HTMLVideoElement;
	let gestureCanvas: HTMLCanvasElement;
	let gestureController: MediaPipeGestureController | null = null;
	
	let scene: any;
	let camera: any;
	let renderer: any;
	let animationId: number | null = null;
	
	let nodes: any[] = [];
	let connections: any[] = [];
	
	let gestureMode = false;
	let currentGesture = '';
	let selectedNode: any = null;
	let rotation = { x: 0.2, y: 0 };
	let zoom = 80;
	
	let videoDevices: MediaDeviceInfo[] = [];
	let selectedDeviceId: string | null = null;
	let showDeviceMenu = false;
	
	// Model tooltip state
	let modelTooltip = {
		visible: false,
		text: '',
		x: 0,
		y: 0
	};
	
	// Model selector panel state (UI-based, not 3D)
	let showModelSelector = false;
	let availableModelsList: { id: string; name: string; color: string; chatCount: number }[] = [];
	
	// Warp effect state
	let isWarping = false;
	let warpSpeed = 0;
	let warpLines: any[] = [];
	
	// Equalizer state
	let eqBars: number[] = new Array(16).fill(0);
	
	const initThreeJS = async () => {
		// @ts-ignore - CDN import
		const THREE = await import('https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js');
		
		scene = new THREE.Scene();
		scene.background = new THREE.Color(0x000008);
		scene.fog = new THREE.Fog(0x000008, 80, 300);
		
		camera = new THREE.PerspectiveCamera(
			75,
			window.innerWidth / window.innerHeight,
			0.1,
			1000
		);
		camera.position.z = zoom;
		
		renderer = new THREE.WebGLRenderer({ 
			canvas: sceneCanvas, 
			antialias: true,
			alpha: true
		});
		renderer.setSize(window.innerWidth, window.innerHeight);
		renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
		
		// Create the scene content first (ensures something renders)
		createChatGraph(THREE);
		
		// Create warp speed lines (hidden initially)
		createWarpLines(THREE);
		
		// Start animation loop
		animate(THREE);
		
		// Apply CSS glow effect to canvas for neon look
		if (sceneCanvas) {
			sceneCanvas.style.filter = 'contrast(1.1) saturate(1.2)';
		}
	};
	
	let dataStreams: any[] = [];
	let buildings: any[] = [];
	let flySpeed = 0;
	let targetBuilding: any = null;
	let cameraTarget = { x: 0, y: 25, z: 0 };
	let cameraWorldPos = { x: 0, z: 0 };
	let electricArcs: any[] = [];
	let hoveredBuilding: any = null;
	
	// Audio reactivity
	let audioContext: AudioContext | null = null;
	let audioAnalyzer: AnalyserNode | null = null;
	let audioDataArray: Uint8Array | null = null;
	let audioEnabled = false;
	let particleSystem: any = null;
	
	// Model Hub - floating AI model representations
	let modelHub: Map<string, any> = new Map(); // modelId -> 3D object
	let hoveredModel: any = null;
	let modelStats: Map<string, { chatCount: number; lastUsed: Date | null }> = new Map();
	
	// Procedural generation settings
	const CHUNK_SIZE = 100;
	const RENDER_DISTANCE = 3; // chunks in each direction
	const BUILDINGS_PER_CHUNK = 8; // Fewer procedural buildings
	let loadedChunks: Map<string, any> = new Map();
	let threeRef: any = null;
	
	// Model colors for chat buildings
	const MODEL_COLORS: Record<string, number> = {
		'gpt': 0x10a37f,      // OpenAI green
		'claude': 0xd97706,   // Anthropic orange
		'gemini': 0x4285f4,   // Google blue
		'llama': 0x0467df,    // Meta blue
		'mistral': 0xff7000,  // Mistral orange
		'ollama': 0xffffff,   // White
		'default': 0x00ffff   // Cyan
	};
	
	const getModelColor = (modelName: string): number => {
		const name = (modelName || '').toLowerCase();
		for (const [key, color] of Object.entries(MODEL_COLORS)) {
			if (name.includes(key)) return color;
		}
		return MODEL_COLORS.default;
	};
	
	// Seeded random for consistent chunk generation
	const seededRandom = (seed: number) => {
		const x = Math.sin(seed * 12.9898 + seed * 78.233) * 43758.5453;
		return x - Math.floor(x);
	};
	
	const getChunkKey = (cx: number, cz: number) => `${cx},${cz}`;
	
	const createChatGraph = async (THREE: any) => {
		threeRef = THREE;
		
		// Ambient and dramatic lighting
		const ambientLight = new THREE.AmbientLight(0x0a0a1a, 0.3);
		scene.add(ambientLight);
		
		// Sweeping spotlights that follow camera
		const spotlight1 = new THREE.SpotLight(0x00ffff, 3, 200, Math.PI / 5, 0.5);
		spotlight1.position.set(50, 100, 50);
		scene.add(spotlight1);
		
		const spotlight2 = new THREE.SpotLight(0xff00ff, 3, 200, Math.PI / 5, 0.5);
		spotlight2.position.set(-50, 100, -50);
		scene.add(spotlight2);
		
		// Flying data particles (will follow camera)
		createParticleSystem(THREE);
		
		// Store for animation
		scene.userData.spotlights = [spotlight1, spotlight2];
		
		// Load user chats and create chat buildings in center
		await loadUserChats(THREE);
		
		// Create Model Hub - small 3D orbs that follow the camera
		createModelHub(THREE);
		
		// Initial chunk loading (procedural buildings in outer areas)
		updateChunks();
	};
	
	// Model Hub - creates small floating orbs that follow the camera
	let modelHubGroup: any = null;
	
	const createModelHub = (THREE: any) => {
		// Get available models from the store (same as chat dropdown)
		const availableModels = $models || [];
		
		// Collect usage stats from chats
		const modelUsage: Map<string, { count: number; lastUsed: number }> = new Map();
		userChats.forEach(chat => {
			let chatModels: string[] = [];
			if (chat.chat?.models && Array.isArray(chat.chat.models)) chatModels = chat.chat.models;
			else if (chat.models && Array.isArray(chat.models)) chatModels = chat.models;
			else if (chat.model) chatModels = [chat.model];
			
			chatModels.forEach((model: string) => {
				if (!model) return;
				const existing = modelUsage.get(model) || { count: 0, lastUsed: 0 };
				existing.count++;
				const chatTime = chat.updated_at || chat.created_at || 0;
				if (chatTime > existing.lastUsed) existing.lastUsed = chatTime;
				modelUsage.set(model, existing);
			});
		});
		
		if (availableModels.length === 0) {
			console.log('No models available for Model Hub');
			return;
		}
		
		console.log(`Model Hub: Found ${availableModels.length} available models`);
		
		// Build the UI list for the panel selector too
		availableModelsList = availableModels.map((model: any) => {
			const modelId = model.id || model.name || 'unknown';
			const modelName = model.name || model.id || 'Unknown Model';
			const stats = modelUsage.get(modelId) || { count: 0, lastUsed: 0 };
			const colorNum = getModelColor(modelId);
			const colorHex = '#' + colorNum.toString(16).padStart(6, '0');
			modelStats.set(modelId, { chatCount: stats.count, lastUsed: stats.lastUsed ? new Date(stats.lastUsed * 1000) : null });
			return { id: modelId, name: modelName, color: colorHex, chatCount: stats.count };
		});
		
		// Create Model Hub group - will follow camera
		modelHubGroup = new THREE.Group();
		modelHubGroup.name = 'modelHub';
		
		// Arrange orbs in a full circular orbit at the top-left of the view
		const orbCount = Math.min(availableModels.length, 12); // Limit to 12 visible orbs
		const orbitRadius = 2.5; // Compact circular orbit radius
		
		availableModels.slice(0, orbCount).forEach((model: any, index: number) => {
			const modelId = model.id || model.name || 'unknown';
			const modelName = model.name || model.id || 'Unknown Model';
			const stats = modelUsage.get(modelId) || { count: 0, lastUsed: 0 };
			
			// Full circle distribution
			const angle = (index / orbCount) * Math.PI * 2;
			const x = Math.cos(angle) * orbitRadius - 10; // Offset to left
			const y = Math.sin(angle) * orbitRadius + 6; // Offset up (top of view)
			const z = -15; // In front of camera
			
			// Create small model orb
			const orbSize = 0.4; // Even smaller
			const color = getModelColor(modelId);
			
			// Wireframe outer shell
			const orbGeometry = new THREE.IcosahedronGeometry(orbSize, 1);
			const orbMaterial = new THREE.MeshBasicMaterial({
				color,
				transparent: true,
				opacity: 0.7,
				wireframe: true
			});
			const orb = new THREE.Mesh(orbGeometry, orbMaterial);
			orb.position.set(x, y, z);
			
			// Inner solid core
			const coreGeometry = new THREE.IcosahedronGeometry(orbSize * 0.5, 1);
			const coreMaterial = new THREE.MeshBasicMaterial({
				color,
				transparent: true,
				opacity: 0.5
			});
			const core = new THREE.Mesh(coreGeometry, coreMaterial);
			orb.add(core);
			
			// Small orbiting ring
			const orbitRing = new THREE.TorusGeometry(orbSize * 1.2, 0.03, 8, 24);
			const orbitMaterial = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.5 });
			const orbit = new THREE.Mesh(orbitRing, orbitMaterial);
			orbit.rotation.x = Math.PI / 3;
			orb.add(orbit);
			
			// Store model data
			orb.userData = {
				isModel: true,
				modelId: modelId,
				modelName: modelName,
				chatCount: stats.count,
				lastUsed: stats.lastUsed,
				baseY: y,
				rotationSpeed: 0.01 + Math.random() * 0.02,
				orbitRing: orbit
			};
			
			modelHubGroup.add(orb);
			modelHub.set(modelId, orb);
		});
		
		// Add to scene (will be repositioned each frame to follow camera)
		scene.add(modelHubGroup);
	};
	
	// Linear timeline settings
	const TIMELINE_SPACING = 30; // Distance between chats on Z-axis
	const LANE_WIDTH = 20; // Width of each model lane on X-axis
	let timelineStart = 0; // Z position of oldest chat
	let timelineEnd = 0; // Z position of newest chat
	
	// Lazy loading pagination state
	let currentPage = 1;
	let hasMoreChats = true;
	let isLoadingMoreChats = false;
	let loadedChatIds = new Set<string>(); // Track which chats are already loaded
	const CHATS_PER_PAGE = 50; // Matches API default
	const LOAD_TRIGGER_DISTANCE = 200; // Z distance from timeline end to trigger loading
	
	// Get date label for a timestamp
	const getDateLabel = (timestamp: number): string => {
		const date = new Date(timestamp);
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' });
	};
	
	// Get current position on timeline based on camera Z
	const getCurrentZone = () => {
		const progress = (cameraWorldPos.z - timelineStart) / (timelineEnd - timelineStart || 1);
		if (progress < 0.2) return 'BEGINNING';
		if (progress < 0.4) return 'EARLY';
		if (progress < 0.6) return 'MIDDLE';
		if (progress < 0.8) return 'RECENT';
		return 'NOW';
	};
	
	// Get time-of-day offset from midday (12:00) - returns -12 to +12 hours
	const getTimeOfDayOffset = (timestamp: number): number => {
		const date = new Date(timestamp * 1000);
		const hours = date.getHours();
		const minutes = date.getMinutes();
		const totalHours = hours + minutes / 60;
		// Offset from midday (12:00) - morning is negative, afternoon/evening is positive
		return totalHours - 12;
	};
	
	const loadUserChats = async (THREE: any) => {
		try {
			// Load first page of chats
			currentPage = 1;
			const chatList = await getChatList(localStorage.token, currentPage, true, true);
			userChats = chatList || [];
			
			if (userChats.length === 0) {
				hasMoreChats = false;
				return;
			}
			
			// Track loaded chat IDs
			userChats.forEach(chat => loadedChatIds.add(chat.id));
			
			// Check if there might be more chats
			hasMoreChats = userChats.length >= CHATS_PER_PAGE;
			
			// Sort chats by creation/update time (newest/latest first at start)
			const sortedChats = [...userChats].sort((a, b) => {
				const timeA = a.created_at || a.updated_at || 0;
				const timeB = b.created_at || b.updated_at || 0;
				return timeB - timeA; // Newest/latest first
			});
			
			const chatCount = sortedChats.length;
			
			// Create timeline markers and buildings
			timelineStart = 0;
			timelineEnd = chatCount * TIMELINE_SPACING;
			
			createTimelineMarkers(THREE, sortedChats.slice(0, chatCount));
			
			// Create buildings along timeline - X position with alternating offset
			for (let i = 0; i < chatCount; i++) {
				const chat = sortedChats[i];
				const timestamp = chat.created_at || chat.updated_at || 0;
				
				// X position based on time of day + alternating offset
				const timeOffset = getTimeOfDayOffset(timestamp);
				const baseX = timeOffset * 5; // Scale factor for spread (wider)
				
				// Alternate left/right from center based on index
				const alternateOffset = (i % 2 === 0) ? -15 : 15;
				const x = baseX + alternateOffset;
				
				const z = i * TIMELINE_SPACING;
				
				const building = createChatBuilding(THREE, chat, x, z, i);
				scene.add(building);
				buildings.push(building);
				chatBuildings.set(chat.id, building);
			}
			
			// Start camera at the oldest chat (beginning of timeline)
			cameraTarget.x = 0;
			cameraTarget.z = -20; // Slightly before the first chat
			cameraTarget.y = 25;
			
			// Create highways between related chats
			createChatHighways(THREE);
			
			// Load folders and create folder nodes
			await loadFolders(THREE);
			
		} catch (error) {
			console.error('Failed to load chats:', error);
		}
	};
	
	// Load folders and create visual nodes for them
	const loadFolders = async (THREE: any) => {
		try {
			const folderList = await getFolders(localStorage.token);
			
			if (!folderList || folderList.length === 0) return;
			
			// Fetch chats for each folder using the folder endpoint
			const chatsByFolder = new Map<string, any[]>();
			
			for (const folderSummary of folderList) {
				try {
					folders.set(folderSummary.id, folderSummary);
					
					// Get chats in this folder from the API
					const folderChats = await getChatsByFolderId(localStorage.token, folderSummary.id);
					
					if (folderChats && folderChats.length > 0) {
						// Store all chat IDs for this folder (for lazy loading updates)
						folderChatIds.set(folderSummary.id, folderChats.map((fc: any) => fc.id));
						
						// Find matching chats from userChats (already loaded buildings)
						const chatsWithBuildings = folderChats.filter((fc: any) => chatBuildings.has(fc.id));
						
						if (chatsWithBuildings.length > 0) {
							chatsByFolder.set(folderSummary.id, chatsWithBuildings);
						}
					}
				} catch (err) {
					console.error(`[Folders] Failed to fetch chats for folder ${folderSummary.id}:`, err);
				}
			}
			
						
			// Create folder nodes and connections
			chatsByFolder.forEach((chatsInFolder, folderId) => {
				const folder = folders.get(folderId);
				if (!folder || chatsInFolder.length === 0) return;
				
				createFolderNode(THREE, folder, chatsInFolder);
			});
			
						
		} catch (error) {
			console.error('Failed to load folders:', error);
		}
	};
	
	// Create a folder node above its chats with connections
	const createFolderNode = (THREE: any, folder: any, chatsInFolder: any[]) => {
		// Find the center position of all chats in this folder
		let sumX = 0, sumZ = 0, minZ = Infinity, maxZ = -Infinity;
		const chatBuildingsInFolder: any[] = [];
		
		chatsInFolder.forEach(chat => {
			const building = chatBuildings.get(chat.id);
			if (building) {
				sumX += building.position.x;
				sumZ += building.position.z;
				minZ = Math.min(minZ, building.position.z);
				maxZ = Math.max(maxZ, building.position.z);
				chatBuildingsInFolder.push(building);
			}
		});
		
		if (chatBuildingsInFolder.length === 0) return;
		
		const centerX = sumX / chatBuildingsInFolder.length;
		const centerZ = (minZ + maxZ) / 2;
		const folderY = 60; // Height above buildings
		
		// Create folder node group
		const folderGroup = new THREE.Group();
		folderGroup.position.set(centerX, folderY, centerZ);
		folderGroup.userData = {
			isFolder: true,
			folderId: folder.id,
			folderName: folder.name,
			chatCount: chatsInFolder.length
		};
		
		// Folder icon - hexagonal prism
		const hexRadius = 4;
		const hexHeight = 2;
		const hexGeometry = new THREE.CylinderGeometry(hexRadius, hexRadius, hexHeight, 6);
		const hexMaterial = new THREE.MeshBasicMaterial({
			color: 0xffaa00, // Orange/gold for folders
			transparent: true,
			opacity: 0.8
		});
		const hexMesh = new THREE.Mesh(hexGeometry, hexMaterial);
		hexMesh.rotation.y = Math.PI / 6; // Rotate to look like a folder icon
		folderGroup.add(hexMesh);
		
		// Glowing ring around folder
		const ringGeometry = new THREE.TorusGeometry(hexRadius + 1, 0.3, 8, 32);
		const ringMaterial = new THREE.MeshBasicMaterial({
			color: 0xffaa00,
			transparent: true,
			opacity: 0.5
		});
		const ring = new THREE.Mesh(ringGeometry, ringMaterial);
		ring.rotation.x = Math.PI / 2;
		ring.userData.rotationSpeed = 0.01;
		folderGroup.add(ring);
		
		// Folder name label (above the node)
		const labelSprite = createTextSprite(THREE, folder.name, 0xffaa00);
		labelSprite.position.set(0, hexHeight + 1.5, 0);
		labelSprite.scale.set(10, 2.5, 1);
		folderGroup.add(labelSprite);
		
		// Chat count indicator (below the node)
		const countSprite = createTextSprite(THREE, `${chatsInFolder.length} chats`, 0xffffff);
		countSprite.position.set(0, -hexHeight - 1, 0);
		countSprite.scale.set(6, 1.5, 1);
		folderGroup.add(countSprite);
		
		scene.add(folderGroup);
		folderNodes.set(folder.id, folderGroup);
		
		// Create connection lines from folder to each chat
		chatBuildingsInFolder.forEach(building => {
			const connection = createFolderConnection(THREE, folderGroup, building);
			if (connection) {
				scene.add(connection);
				folderConnections.push(connection);
			}
		});
	};
	
	// Create a glowing connection line from folder node to chat building
	const createFolderConnection = (THREE: any, folderNode: any, chatBuilding: any): any => {
		const startPos = folderNode.position;
		const endPos = chatBuilding.position;
		const buildingHeight = chatBuilding.userData?.height || 10;
		
		// Create curved connection using quadratic bezier
		const midY = (startPos.y + buildingHeight) / 2 + 10;
		const curve = new THREE.QuadraticBezierCurve3(
			new THREE.Vector3(startPos.x, startPos.y - 2, startPos.z),
			new THREE.Vector3(
				(startPos.x + endPos.x) / 2,
				midY,
				(startPos.z + endPos.z) / 2
			),
			new THREE.Vector3(endPos.x, buildingHeight + 2, endPos.z)
		);
		
		const points = curve.getPoints(20);
		const geometry = new THREE.BufferGeometry().setFromPoints(points);
		
		// Dashed line material for folder connections
		const material = new THREE.LineDashedMaterial({
			color: 0xffaa00,
			transparent: true,
			opacity: 0.4,
			dashSize: 2,
			gapSize: 1
		});
		
		const line = new THREE.Line(geometry, material);
		line.computeLineDistances(); // Required for dashed lines
		line.userData = {
			isFolderConnection: true,
			folderId: folderNode.userData.folderId,
			chatId: chatBuilding.userData.chatId
		};
		
		return line;
	};
	
	// Lazy load more chats when approaching the end of the timeline
	const loadMoreChats = async () => {
		if (!hasMoreChats || isLoadingMoreChats || !threeRef) return;
		
		isLoadingMoreChats = true;
		console.log(`[Timeline] Loading page ${currentPage + 1}...`);
		
		try {
			const nextPage = currentPage + 1;
			const chatList = await getChatList(localStorage.token, nextPage, true, true);
			
			if (!chatList || chatList.length === 0) {
				hasMoreChats = false;
				console.log('[Timeline] No more chats to load');
				isLoadingMoreChats = false;
				return;
			}
			
			// Filter out already loaded chats
			const newChats = chatList.filter((chat: any) => !loadedChatIds.has(chat.id));
			
			if (newChats.length === 0) {
				hasMoreChats = chatList.length >= CHATS_PER_PAGE;
				currentPage = nextPage;
				isLoadingMoreChats = false;
				return;
			}
			
			console.log(`[Timeline] Loaded ${newChats.length} new chats`);
			
			// Track new chat IDs
			newChats.forEach((chat: any) => loadedChatIds.add(chat.id));
			
			// Add to userChats array
			userChats = [...userChats, ...newChats];
			
			// Sort new chats by time (oldest first for appending to timeline)
			const sortedNewChats = [...newChats].sort((a: any, b: any) => {
				const timeA = a.created_at || a.updated_at || 0;
				const timeB = b.created_at || b.updated_at || 0;
				return timeB - timeA; // Newest first (will be placed at higher Z)
			});
			
			// Get current building count to calculate Z positions
			const existingBuildingCount = chatBuildings.size;
			
			// Create buildings for new chats
			const THREE = threeRef;
			for (let i = 0; i < sortedNewChats.length; i++) {
				const chat = sortedNewChats[i];
				const globalIndex = existingBuildingCount + i;
				const timestamp = chat.created_at || chat.updated_at || 0;
				
				// X position based on time of day + alternating offset
				const timeOffset = getTimeOfDayOffset(timestamp);
				const baseX = timeOffset * 5;
				const alternateOffset = (globalIndex % 2 === 0) ? -15 : 15;
				const x = baseX + alternateOffset;
				
				const z = globalIndex * TIMELINE_SPACING;
				
				const building = createChatBuilding(THREE, chat, x, z, globalIndex);
				scene.add(building);
				buildings.push(building);
				chatBuildings.set(chat.id, building);
				
				// Add date marker if needed (at month boundaries)
				addDateMarkerIfNeeded(THREE, chat, z);
			}
			
			// Update timeline end position
			timelineEnd = chatBuildings.size * TIMELINE_SPACING;
			
			// Update "PAST" marker position
			updatePastMarker(THREE);
			
			// Create highways for new buildings
			createHighwaysForNewBuildings(THREE, sortedNewChats);
			
			// Update folder nodes for newly loaded chats
			updateFolderNodesForNewChats(THREE, sortedNewChats);
			
			currentPage = nextPage;
			hasMoreChats = chatList.length >= CHATS_PER_PAGE;
			
			console.log(`[Timeline] Timeline now has ${chatBuildings.size} chats, hasMore: ${hasMoreChats}`);
			
		} catch (error) {
			console.error('Failed to load more chats:', error);
		} finally {
			isLoadingMoreChats = false;
		}
	};
	
	// Track last date marker to avoid duplicates
	let lastMarkerMonth = -1;
	let lastMarkerYear = -1;
	
	const addDateMarkerIfNeeded = (THREE: any, chat: any, z: number) => {
		const timestamp = (chat.created_at || chat.updated_at || 0) * 1000;
		const date = new Date(timestamp);
		const month = date.getMonth();
		const year = date.getFullYear();
		
		if (month !== lastMarkerMonth || year !== lastMarkerYear) {
			lastMarkerMonth = month;
			lastMarkerYear = year;
			
			// Vertical marker line
			const markerGeometry = new THREE.BufferGeometry().setFromPoints([
				new THREE.Vector3(-30, 0, z),
				new THREE.Vector3(30, 0, z)
			]);
			const markerColor = 0xff00ff;
			const markerMaterial = new THREE.LineBasicMaterial({ color: markerColor, transparent: true, opacity: 0.4 });
			scene.add(new THREE.Line(markerGeometry, markerMaterial));
			
			// Date label sprite
			const dateLabel = getDateLabel(timestamp);
			const labelSprite = createTextSprite(THREE, dateLabel, markerColor);
			labelSprite.position.set(-35, 25, z);
			labelSprite.scale.set(10, 2.5, 1);
			scene.add(labelSprite);
		}
	};
	
	// Reference to the "PAST" marker sprite for repositioning
	let pastMarkerSprite: any = null;
	
	const updatePastMarker = (THREE: any) => {
		const newZ = chatBuildings.size * TIMELINE_SPACING + 10;
		
		if (pastMarkerSprite) {
			pastMarkerSprite.position.z = newZ;
		} else {
			// Create if doesn't exist
			pastMarkerSprite = createTextSprite(THREE, 'PAST ▶', 0xff00ff);
			pastMarkerSprite.position.set(0, 100, newZ);
			pastMarkerSprite.scale.set(12, 3, 1);
			scene.add(pastMarkerSprite);
		}
	};
	
	const createHighwaysForNewBuildings = (THREE: any, newChats: any[]) => {
		// Connect new buildings to existing timeline
		const allBuildings = Array.from(chatBuildings.values());
		const sortedByZ = [...allBuildings].sort((a, b) => a.position.z - b.position.z);
		
		// Find where new buildings start and connect them
		for (let i = 0; i < sortedByZ.length - 1; i++) {
			const curr = sortedByZ[i];
			const next = sortedByZ[i + 1];
			
			// Check if this is a new connection (one of them is a new chat)
			const currIsNew = newChats.some(c => c.id === curr.userData.chatId);
			const nextIsNew = newChats.some(c => c.id === next.userData.chatId);
			
			if (currIsNew || nextIsNew) {
				const dz = next.position.z - curr.position.z;
				if (dz < TIMELINE_SPACING * 2) {
					const highway = createDataHighway(THREE, curr, next);
					if (highway) scene.add(highway.group);
				}
			}
		}
	};
	
	// Store folder chat IDs for lazy loading updates
	let folderChatIds: Map<string, string[]> = new Map();
	
	// Update folder nodes when new chats are loaded (add connections for chats in existing folders)
	const updateFolderNodesForNewChats = (THREE: any, newChats: any[]) => {
		// Check each folder to see if any new chats belong to it
		folderChatIds.forEach((chatIds, folderId) => {
			if (chatIds.length === 0) return;
			
			// Find new chats that belong to this folder
			const newChatsInFolder = newChats.filter(chat => chatIds.includes(chat.id));
			if (newChatsInFolder.length === 0) return;
			
			const folder = folders.get(folderId);
			const folderNode = folderNodes.get(folderId);
			if (!folderNode) {
				// Folder node doesn't exist yet - create it with all visible chats
				const allChatsInFolder = userChats.filter(chat => chatIds.includes(chat.id));
				if (allChatsInFolder.length > 0 && folder) {
					createFolderNode(THREE, folder, allChatsInFolder);
				}
				return;
			}
			
			// Add connections for new chats
			newChatsInFolder.forEach(chat => {
				const building = chatBuildings.get(chat.id);
				if (building) {
					const connection = createFolderConnection(THREE, folderNode, building);
					if (connection) {
						scene.add(connection);
						folderConnections.push(connection);
					}
				}
			});
			
			// Update folder node position to center over all its visible chats
			const allChatsInFolder = userChats.filter(chat => chatIds.includes(chat.id));
			let sumX = 0, sumZ = 0, count = 0;
			allChatsInFolder.forEach(chat => {
				const building = chatBuildings.get(chat.id);
				if (building) {
					sumX += building.position.x;
					sumZ += building.position.z;
					count++;
				}
			});
			
			if (count > 0) {
				folderNode.position.x = sumX / count;
				folderNode.position.z = sumZ / count;
				
				// Update chat count label
				folderNode.userData.chatCount = count;
				const countSprite = folderNode.children.find((c: any) => 
					c.isSprite && c.position.y > 4
				);
				if (countSprite) {
					// Remove old sprite and create new one with updated count
					folderNode.remove(countSprite);
					const newCountSprite = createTextSprite(THREE, `${count} chats`, 0xffffff);
					newCountSprite.position.set(0, 8, 0);
					newCountSprite.scale.set(8, 2, 1);
					folderNode.add(newCountSprite);
				}
			}
		});
	};
	
	const createTimelineMarkers = (THREE: any, sortedChats: any[]) => {
		const railLength = sortedChats.length * TIMELINE_SPACING + 50;
		
		// Create date markers along timeline
		let lastMonth = -1;
		let lastYear = -1;
		
		for (let i = 0; i < sortedChats.length; i++) {
			const chat = sortedChats[i];
			const timestamp = (chat.created_at || chat.updated_at || 0) * 1000;
			const date = new Date(timestamp);
			const month = date.getMonth();
			const year = date.getFullYear();
			const z = i * TIMELINE_SPACING;
			
			// Add marker at month boundaries
			if (month !== lastMonth || year !== lastYear) {
				lastMonth = month;
				lastYear = year;
				
				// Vertical marker line
				const markerGeometry = new THREE.BufferGeometry().setFromPoints([
					new THREE.Vector3(-30, 0, z),
					new THREE.Vector3(30, 0, z)
				]);
				const markerColor = 0xff00ff;
				const markerMaterial = new THREE.LineBasicMaterial({ color: markerColor, transparent: true, opacity: 0.4 });
				scene.add(new THREE.Line(markerGeometry, markerMaterial));
				
				// Date label sprite - positioned low near grid
				const dateLabel = getDateLabel(timestamp);
				const labelSprite = createTextSprite(THREE, dateLabel, markerColor);
				labelSprite.position.set(-35, 25, z);
				labelSprite.scale.set(10, 2.5, 1);
				scene.add(labelSprite);
			}
		}
		
		// Add "NOW" marker at beginning (newest chats) - high above buildings
		const nowSprite = createTextSprite(THREE, '◀ NOW', 0x00ffff);
		nowSprite.position.set(0, 100, -15);
		nowSprite.scale.set(12, 3, 1);
		scene.add(nowSprite);
		
		// Add "PAST" marker at end (oldest chats) - high above buildings
		if (sortedChats.length > 0) {
			const pastSprite = createTextSprite(THREE, 'PAST ▶', 0xff00ff);
			pastSprite.position.set(0, 100, sortedChats.length * TIMELINE_SPACING + 10);
			pastSprite.scale.set(12, 3, 1);
			scene.add(pastSprite);
		}
	};
	
	// Extract message count from chat data
	const getMessageCount = (chat: any): number => {
		// Try different paths to find message count
		// 1. Check if messages is an object (history format)
		const historyMessages = chat.chat?.history?.messages || chat.history?.messages;
		if (historyMessages && typeof historyMessages === 'object') {
			return Object.keys(historyMessages).length;
		}
		
		// 2. Check if messages is an array
		const arrayMessages = chat.chat?.messages || chat.messages;
		if (Array.isArray(arrayMessages)) {
			return arrayMessages.length;
		}
		
		// 3. Fallback - estimate from title length or default
		return 3;
	};
	
	// Create text sprite using canvas texture
	const createTextSprite = (THREE: any, text: string, color: number) => {
		const canvas = document.createElement('canvas');
		const context = canvas.getContext('2d')!;
		canvas.width = 512;
		canvas.height = 128;
		
		// Clear canvas
		context.clearRect(0, 0, canvas.width, canvas.height);
		
		// Draw background with slight transparency
		context.fillStyle = 'rgba(0, 0, 0, 0.6)';
		context.roundRect(10, 10, canvas.width - 20, canvas.height - 20, 10);
		context.fill();
		
		// Draw border
		const hexColor = '#' + color.toString(16).padStart(6, '0');
		context.strokeStyle = hexColor;
		context.lineWidth = 3;
		context.roundRect(10, 10, canvas.width - 20, canvas.height - 20, 10);
		context.stroke();
		
		// Draw text
		context.font = 'bold 36px Courier New, monospace';
		context.fillStyle = hexColor;
		context.textAlign = 'center';
		context.textBaseline = 'middle';
		context.shadowColor = hexColor;
		context.shadowBlur = 10;
		context.fillText(text, canvas.width / 2, canvas.height / 2);
		
		// Create texture and sprite
		const texture = new THREE.CanvasTexture(canvas);
		texture.needsUpdate = true;
		
		const spriteMaterial = new THREE.SpriteMaterial({
			map: texture,
			transparent: true,
			depthTest: false
		});
		
		const sprite = new THREE.Sprite(spriteMaterial);
		sprite.scale.set(12, 3, 1); // Adjust scale for readability
		
		return sprite;
	};
	
	const createChatBuilding = (THREE: any, chat: any, x: number, z: number, index: number) => {
		const buildingGroup = new THREE.Group();
		
		// Height based on message count
		const messageCount = getMessageCount(chat);
		const height = Math.min(8 + messageCount * 3, 80); // More dramatic height variation
		const width = 2.5 + Math.min(messageCount * 0.05, 1); // Width also scales slightly with messages
		
		// Color based on model used
		const modelName = chat.chat?.models?.[0] || chat.models?.[0] || 'default';
		const mainColor = getModelColor(modelName);
		
		// === OUTER WIREFRAME SHELL ===
		const outerGeometry = new THREE.CylinderGeometry(width, width * 1.1, height, 8, 4, true);
		const outerMaterial = new THREE.MeshBasicMaterial({
			color: mainColor,
			wireframe: true,
			transparent: true,
			opacity: 0.4
		});
		const outerShell = new THREE.Mesh(outerGeometry, outerMaterial);
		outerShell.position.y = height / 2;
		buildingGroup.add(outerShell);
		
		// === INNER WIREFRAME CORE ===
		const innerGeometry = new THREE.CylinderGeometry(width * 0.6, width * 0.7, height * 0.9, 6, 3, true);
		const innerMaterial = new THREE.MeshBasicMaterial({
			color: mainColor,
			wireframe: true,
			transparent: true,
			opacity: 0.7
		});
		const innerCore = new THREE.Mesh(innerGeometry, innerMaterial);
		innerCore.position.y = height / 2;
		buildingGroup.add(innerCore);
		
		// === GLOWING EDGE LINES ===
		const edgePoints = [];
		for (let i = 0; i <= 8; i++) {
			const edgeAngle = (i / 8) * Math.PI * 2;
			edgePoints.push(new THREE.Vector3(
				Math.cos(edgeAngle) * width,
				0,
				Math.sin(edgeAngle) * width
			));
		}
		const edgeGeometry = new THREE.BufferGeometry().setFromPoints(edgePoints);
		const edgeMaterial = new THREE.LineBasicMaterial({ color: mainColor, transparent: true, opacity: 0.9 });
		
		// Bottom edge
		const bottomEdge = new THREE.Line(edgeGeometry, edgeMaterial);
		buildingGroup.add(bottomEdge);
		
		// Top edge
		const topEdge = new THREE.Line(edgeGeometry.clone(), edgeMaterial);
		topEdge.position.y = height;
		buildingGroup.add(topEdge);
		
		// === VERTICAL GLOWING LINES ===
		for (let i = 0; i < 8; i++) {
			const lineAngle = (i / 8) * Math.PI * 2;
			const lineGeometry = new THREE.BufferGeometry().setFromPoints([
				new THREE.Vector3(Math.cos(lineAngle) * width, 0, Math.sin(lineAngle) * width),
				new THREE.Vector3(Math.cos(lineAngle) * width * 1.05, height, Math.sin(lineAngle) * width * 1.05)
			]);
			const lineMaterial = new THREE.LineBasicMaterial({ 
				color: mainColor, 
				transparent: true, 
				opacity: i % 2 === 0 ? 0.9 : 0.5 
			});
			const vertLine = new THREE.Line(lineGeometry, lineMaterial);
			buildingGroup.add(vertLine);
		}
		
		// === FLOOR PLATES (horizontal sections) ===
		const floorCount = Math.floor(height / 8);
		for (let f = 1; f < floorCount; f++) {
			const floorY = f * 8;
			const floorRadius = width * (1 - f * 0.02);
			const floorGeometry = new THREE.RingGeometry(floorRadius * 0.3, floorRadius, 8);
			const floorMaterial = new THREE.MeshBasicMaterial({
				color: mainColor,
				transparent: true,
				opacity: 0.15,
				side: THREE.DoubleSide
			});
			const floor = new THREE.Mesh(floorGeometry, floorMaterial);
			floor.rotation.x = -Math.PI / 2;
			floor.position.y = floorY;
			buildingGroup.add(floor);
		}
		
		// === GLOWING BEACON ON TOP ===
		const beaconGeometry = new THREE.OctahedronGeometry(1.2, 0);
		const beaconMaterial = new THREE.MeshBasicMaterial({
			color: mainColor,
			transparent: true,
			opacity: 0.95
		});
		const beacon = new THREE.Mesh(beaconGeometry, beaconMaterial);
		beacon.position.y = height + 2;
		beacon.userData.rotationSpeed = 0.02;
		buildingGroup.add(beacon);
		
		// Beacon glow sphere
		const glowGeometry = new THREE.SphereGeometry(2.5, 16, 16);
		const glowMaterial = new THREE.MeshBasicMaterial({
			color: mainColor,
			transparent: true,
			opacity: 0.12
		});
		const glow = new THREE.Mesh(glowGeometry, glowMaterial);
		glow.position.y = height + 2;
		buildingGroup.add(glow);
		
		// === FLOATING TEXT LABEL ===
		const chatTitle = chat.title || 'Untitled';
		const truncatedTitle = chatTitle.length > 20 ? chatTitle.substring(0, 18) + '...' : chatTitle;
		const labelSprite = createTextSprite(THREE, truncatedTitle, mainColor);
		labelSprite.position.y = height + 6;
		labelSprite.userData.isLabel = true;
		buildingGroup.add(labelSprite);
		
		// === ORBITING DATA RINGS ===
		const ringCount = Math.max(1, Math.floor(height / 12));
		for (let r = 0; r < ringCount; r++) {
			const ringRadius = width + 0.8 + r * 0.3;
			const ringGeometry = new THREE.TorusGeometry(ringRadius, 0.06, 8, 32);
			const ringMaterial = new THREE.MeshBasicMaterial({
				color: mainColor,
				transparent: true,
				opacity: 0.6
			});
			const ring = new THREE.Mesh(ringGeometry, ringMaterial);
			ring.position.y = 8 + r * 12;
			ring.rotation.x = Math.PI / 2 + (Math.random() - 0.5) * 0.3;
			ring.userData.rotationSpeed = (0.01 + Math.random() * 0.02) * (r % 2 === 0 ? 1 : -1);
			buildingGroup.add(ring);
		}
		
		// === DATA PARTICLES AROUND BUILDING ===
		const particleCount = 20;
		const particleGeometry = new THREE.BufferGeometry();
		const particlePositions = new Float32Array(particleCount * 3);
		for (let p = 0; p < particleCount; p++) {
			const pAngle = Math.random() * Math.PI * 2;
			const pRadius = width + 1 + Math.random() * 2;
			const pHeight = Math.random() * height;
			particlePositions[p * 3] = Math.cos(pAngle) * pRadius;
			particlePositions[p * 3 + 1] = pHeight;
			particlePositions[p * 3 + 2] = Math.sin(pAngle) * pRadius;
		}
		particleGeometry.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
		const particleMaterial = new THREE.PointsMaterial({
			color: mainColor,
			size: 0.3,
			transparent: true,
			opacity: 0.8
		});
		const particles = new THREE.Points(particleGeometry, particleMaterial);
		particles.userData.isParticle = true;
		buildingGroup.add(particles);
		
		buildingGroup.position.set(x, 0, z);
		
		// === KNOWLEDGE BASE SATELLITES ===
		const knowledgeBases = extractKnowledgeBases(chat);
		const kbColor = 0xffff00; // Yellow for knowledge bases
		
		for (let k = 0; k < knowledgeBases.length; k++) {
			const kb = knowledgeBases[k];
			const kbAngle = (k / Math.max(knowledgeBases.length, 1)) * Math.PI * 2;
			const kbRadius = width + 4;
			const kbHeight = height * 0.6;
			
			// KB satellite - icosahedron shape
			const kbGeometry = new THREE.IcosahedronGeometry(1, 0);
			const kbMaterial = new THREE.MeshBasicMaterial({
				color: kbColor,
				wireframe: true,
				transparent: true,
				opacity: 0.8
			});
			const kbMesh = new THREE.Mesh(kbGeometry, kbMaterial);
			kbMesh.position.set(
				Math.cos(kbAngle) * kbRadius,
				kbHeight,
				Math.sin(kbAngle) * kbRadius
			);
			kbMesh.userData = { isKB: true, kbName: kb.name, orbitAngle: kbAngle, orbitRadius: kbRadius, orbitHeight: kbHeight };
			buildingGroup.add(kbMesh);
			
			// KB glow
			const kbGlowGeometry = new THREE.IcosahedronGeometry(1.5, 0);
			const kbGlowMaterial = new THREE.MeshBasicMaterial({
				color: kbColor,
				transparent: true,
				opacity: 0.15
			});
			const kbGlow = new THREE.Mesh(kbGlowGeometry, kbGlowMaterial);
			kbGlow.position.copy(kbMesh.position);
			kbGlow.userData = { isKBGlow: true, orbitAngle: kbAngle, orbitRadius: kbRadius, orbitHeight: kbHeight };
			buildingGroup.add(kbGlow);
			
			// Connection line from building to KB
			const connectionGeometry = new THREE.BufferGeometry().setFromPoints([
				new THREE.Vector3(0, kbHeight, 0),
				new THREE.Vector3(Math.cos(kbAngle) * kbRadius, kbHeight, Math.sin(kbAngle) * kbRadius)
			]);
			const connectionMaterial = new THREE.LineBasicMaterial({
				color: kbColor,
				transparent: true,
				opacity: 0.4
			});
			const connectionLine = new THREE.Line(connectionGeometry, connectionMaterial);
			buildingGroup.add(connectionLine);
		}
		
		buildingGroup.userData = { 
			height, 
			chatId: chat.id, 
			chatTitle: chat.title || 'Untitled',
			chatData: chat,
			isChat: true,
			modelName,
			knowledgeBases
		};
		
		return buildingGroup;
	};
	
	// Extract knowledge bases/collections from chat data
	const extractKnowledgeBases = (chat: any): Array<{name: string, type: string, id?: string}> => {
		const kbs: Array<{name: string, type: string, id?: string}> = [];
		const seen = new Set<string>();
		
		// Check chat files
		const chatFiles = chat.chat?.files || chat.files || [];
		for (const file of chatFiles) {
			if (file.type === 'collection' && file.name && !seen.has(file.name)) {
				kbs.push({ name: file.name, type: 'collection', id: file.id });
				seen.add(file.name);
			} else if (file.collection_name && !seen.has(file.collection_name)) {
				kbs.push({ name: file.collection_name, type: 'file', id: file.id });
				seen.add(file.collection_name);
			}
		}
		
		// Check message files for knowledge bases
		const messages = chat.chat?.messages || chat.history?.messages || {};
		for (const msgId of Object.keys(messages)) {
			const msg = messages[msgId];
			const msgFiles = msg?.files || [];
			for (const file of msgFiles) {
				if (file.type === 'collection' && file.name && !seen.has(file.name)) {
					kbs.push({ name: file.name, type: 'collection', id: file.id });
					seen.add(file.name);
				} else if (file.collection_name && !seen.has(file.collection_name)) {
					kbs.push({ name: file.collection_name, type: 'file', id: file.id });
					seen.add(file.collection_name);
				}
			}
		}
		
		return kbs;
	};
	
	const createChatHighways = (THREE: any) => {
		const chatArray = Array.from(chatBuildings.values());
		
		// Group buildings by model for topology connections
		const buildingsByModel: Record<string, any[]> = {};
		for (const building of chatArray) {
			const modelName = building.userData.modelName || 'default';
			const modelKey = modelName.split(':')[0].split('/').pop() || 'default';
			if (!buildingsByModel[modelKey]) buildingsByModel[modelKey] = [];
			buildingsByModel[modelKey].push(building);
		}
		
		// Connect buildings of the same model (topology)
		for (const [modelKey, modelBuildings] of Object.entries(buildingsByModel)) {
			if (modelBuildings.length < 2) continue;
			
			// Connect each building to its nearest neighbor of same model
			for (let i = 0; i < modelBuildings.length; i++) {
				const building = modelBuildings[i];
				let nearestDist = Infinity;
				let nearestBuilding = null;
				
				for (let j = 0; j < modelBuildings.length; j++) {
					if (i === j) continue;
					const other = modelBuildings[j];
					const dx = building.position.x - other.position.x;
					const dz = building.position.z - other.position.z;
					const dist = Math.sqrt(dx * dx + dz * dz);
					
					if (dist < nearestDist && dist < 50) { // Max connection distance
						nearestDist = dist;
						nearestBuilding = other;
					}
				}
				
				if (nearestBuilding) {
					const highway = createDataHighway(THREE, building, nearestBuilding);
					if (highway) scene.add(highway.group);
				}
			}
		}
		
		// Connect sequential chats along timeline (chronological flow)
		const sortedByZ = [...chatArray].sort((a, b) => a.position.z - b.position.z);
		for (let i = 0; i < sortedByZ.length - 1; i++) {
			const curr = sortedByZ[i];
			const next = sortedByZ[i + 1];
			
			// Only connect if they're close enough on the timeline
			const dz = next.position.z - curr.position.z;
			if (dz < TIMELINE_SPACING * 2) {
				const highway = createDataHighway(THREE, curr, next);
				if (highway) scene.add(highway.group);
			}
		}
	};
	
	const createParticleSystem = (THREE: any) => {
		const particleCount = 800; // More particles for finer equalizer granularity
		const particlesGeometry = new THREE.BufferGeometry();
		const positions = new Float32Array(particleCount * 3);
		const colors = new Float32Array(particleCount * 3);
		const velocities: number[] = [];
		const packetData: { axis: string; direction: number; speed: number; gridLine: number }[] = [];
		
		for (let i = 0; i < particleCount; i++) {
			// Start particles on grid lines
			const axis = Math.random() < 0.5 ? 'x' : 'z'; // Travel along X or Z axis
			const gridLine = Math.floor(Math.random() * 20 - 10) * 15; // Grid line position
			const direction = Math.random() < 0.5 ? 1 : -1;
			const speed = 0.3 + Math.random() * 0.5;
			
			let x, z;
			if (axis === 'x') {
				// Travel along X, fixed Z on grid
				x = (Math.random() - 0.5) * 300;
				z = gridLine;
			} else {
				// Travel along Z, fixed X on grid
				x = gridLine;
				z = (Math.random() - 0.5) * 300;
			}
			const y = 0.5 + Math.random() * 2; // Low to the ground, on grid
			
			positions[i * 3] = x;
			positions[i * 3 + 1] = y;
			positions[i * 3 + 2] = z;
			
			if (axis === 'x') {
				velocities.push(direction * speed, 0, 0);
			} else {
				velocities.push(0, 0, direction * speed);
			}
			
			packetData.push({ axis, direction, speed, gridLine });
			
			// Color - mostly cyan with some magenta
			const colorChoice = Math.random();
			if (colorChoice < 0.7) {
				colors[i * 3] = 0; colors[i * 3 + 1] = 1; colors[i * 3 + 2] = 1; // Cyan
			} else {
				colors[i * 3] = 1; colors[i * 3 + 1] = 0; colors[i * 3 + 2] = 1; // Magenta
			}
		}
		
		particlesGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
		particlesGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
		
		const particlesMaterial = new THREE.PointsMaterial({
			size: 0.5,
			transparent: true,
			opacity: 0.9,
			vertexColors: true,
			blending: THREE.AdditiveBlending
		});
		
		const particles = new THREE.Points(particlesGeometry, particlesMaterial);
		particles.userData.velocities = velocities;
		particles.userData.packetData = packetData;
		scene.add(particles);
		scene.userData.particles = particles;
		particleSystem = particles;
	};
	
	const createWarpLines = (THREE: any) => {
		if (!scene) return;
		
		// Create streaking lines for warp speed effect
		const lineCount = 150;
		const warpGroup = new THREE.Group();
		warpGroup.visible = false;
		warpLines = []; // Reset array
		
		for (let i = 0; i < lineCount; i++) {
			const length = 5 + Math.random() * 15;
			const geometry = new THREE.BufferGeometry().setFromPoints([
				new THREE.Vector3(0, 0, 0),
				new THREE.Vector3(0, 0, -length)
			]);
			
			const color = Math.random() > 0.5 ? 0x00ffff : 0xff00ff;
			const material = new THREE.LineBasicMaterial({
				color,
				transparent: true,
				opacity: 0.7
			});
			
			const line = new THREE.Line(geometry, material);
			
			// Position randomly around the camera view
			const angle = Math.random() * Math.PI * 2;
			const radius = 5 + Math.random() * 25;
			line.position.x = Math.cos(angle) * radius;
			line.position.y = Math.sin(angle) * radius - 5;
			line.position.z = -20 - Math.random() * 40;
			
			line.userData.baseZ = line.position.z;
			line.userData.speed = 2 + Math.random() * 3;
			
			warpGroup.add(line);
			warpLines.push(line);
		}
		
		scene.add(warpGroup);
		scene.userData.warpGroup = warpGroup;
	};
	
	const startWarp = () => {
		isWarping = true;
		warpSpeed = 0;
		if (scene?.userData?.warpGroup) {
			scene.userData.warpGroup.visible = true;
		}
		// Intensify canvas filter during warp
		if (sceneCanvas) {
			sceneCanvas.style.filter = 'contrast(1.3) saturate(1.5) brightness(1.2)';
		}
	};
	
	const stopWarp = () => {
		isWarping = false;
		if (scene?.userData?.warpGroup) {
			scene.userData.warpGroup.visible = false;
		}
		// Reset canvas filter
		if (sceneCanvas) {
			sceneCanvas.style.filter = 'contrast(1.1) saturate(1.2)';
		}
	};
	
	const generateChunk = (chunkX: number, chunkZ: number) => {
		const THREE = threeRef;
		if (!THREE) return null;
		
		const chunkGroup = new THREE.Group();
		
		// Ground grid for this chunk - endless cyberspace floor
		const gridHelper = new THREE.GridHelper(CHUNK_SIZE, 20, 0x00ffff, 0x002233);
		gridHelper.position.set(chunkX * CHUNK_SIZE, 0, chunkZ * CHUNK_SIZE);
		chunkGroup.add(gridHelper);
		
		// Elevated grid - ceiling effect
		const gridHelper2 = new THREE.GridHelper(CHUNK_SIZE, 10, 0xff00ff, 0x220022);
		gridHelper2.position.set(chunkX * CHUNK_SIZE, 70, chunkZ * CHUNK_SIZE);
		gridHelper2.material.opacity = 0.15;
		gridHelper2.material.transparent = true;
		chunkGroup.add(gridHelper2);
		
		// No procedural buildings - only user chats are shown
		
		chunkGroup.userData = { chunkX, chunkZ, buildings: [] };
		return chunkGroup;
	};
	
	const createProceduralBuilding = (THREE: any, seed: number, worldX: number, worldZ: number) => {
		const buildingGroup = new THREE.Group();
		
		// Procedural building properties
		const buildingType = Math.floor(seededRandom(seed) * 5); // 5 building types
		const height = seededRandom(seed + 10) * 50 + 10;
		const width = seededRandom(seed + 20) * 3 + 2;
		const colorType = Math.floor(seededRandom(seed + 30) * 3);
		
		const colors = [0x00ffff, 0xff00ff, 0x0080ff];
		const mainColor = colors[colorType];
		const altColor = colors[(colorType + 1) % 3];
		
		switch (buildingType) {
			case 0: // Classic tower
				createClassicTower(THREE, buildingGroup, height, width, mainColor);
				break;
			case 1: // Pyramid data structure
				createPyramidTower(THREE, buildingGroup, height, width, mainColor, altColor);
				break;
			case 2: // Cylindrical server
				createCylinderTower(THREE, buildingGroup, height, width, mainColor);
				break;
			case 3: // Stacked blocks
				createStackedTower(THREE, buildingGroup, height, width, mainColor, altColor, seed);
				break;
			case 4: // Antenna spire
				createSpireTower(THREE, buildingGroup, height, width, mainColor, altColor);
				break;
		}
		
		// Add beacon on top
		const beaconGeometry = new THREE.SphereGeometry(0.6, 8, 8);
		const beaconMaterial = new THREE.MeshBasicMaterial({
			color: mainColor,
			transparent: true,
			opacity: 0.9
		});
		const beacon = new THREE.Mesh(beaconGeometry, beaconMaterial);
		beacon.position.y = height + 1;
		buildingGroup.add(beacon);
		
		// Beacon glow
		const glowGeometry = new THREE.SphereGeometry(1.2, 8, 8);
		const glowMaterial = new THREE.MeshBasicMaterial({
			color: mainColor,
			transparent: true,
			opacity: 0.15
		});
		const glow = new THREE.Mesh(glowGeometry, glowMaterial);
		glow.position.y = height + 1;
		buildingGroup.add(glow);
		
		// Data rings
		const ringCount = Math.floor(height / 12);
		for (let r = 0; r < ringCount; r++) {
			const ringGeometry = new THREE.TorusGeometry(width + 0.5, 0.08, 8, 16);
			const ringMaterial = new THREE.MeshBasicMaterial({
				color: seededRandom(seed + r * 100) > 0.5 ? mainColor : altColor,
				transparent: true,
				opacity: 0.5
			});
			const ring = new THREE.Mesh(ringGeometry, ringMaterial);
			ring.position.y = (r + 1) * 12;
			ring.rotation.x = Math.PI / 2;
			ring.userData.rotationSpeed = (seededRandom(seed + r * 200) - 0.5) * 0.04;
			buildingGroup.add(ring);
		}
		
		buildingGroup.position.set(worldX, 0, worldZ);
		buildingGroup.userData = { height, seed };
		buildings.push(buildingGroup);
		
		return buildingGroup;
	};
	
	const createClassicTower = (THREE: any, group: any, height: number, width: number, color: number) => {
		// Outer wireframe shell
		const geometry = new THREE.BoxGeometry(width, height, width, 2, 4, 2);
		const wireframeMat = new THREE.MeshBasicMaterial({ color, wireframe: true, transparent: true, opacity: 0.5 });
		const wireframe = new THREE.Mesh(geometry, wireframeMat);
		wireframe.position.y = height / 2;
		group.add(wireframe);
		
		// Glowing edges
		const edges = new THREE.EdgesGeometry(new THREE.BoxGeometry(width, height, width));
		const edgeLine = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.9 }));
		edgeLine.position.y = height / 2;
		group.add(edgeLine);
		
		// Inner core wireframe
		const innerGeometry = new THREE.BoxGeometry(width * 0.6, height * 0.9, width * 0.6, 1, 3, 1);
		const innerMat = new THREE.MeshBasicMaterial({ color, wireframe: true, transparent: true, opacity: 0.3 });
		const inner = new THREE.Mesh(innerGeometry, innerMat);
		inner.position.y = height / 2;
		group.add(inner);
		
		// Floor plates
		const floors = Math.floor(height / 10);
		for (let f = 1; f < floors; f++) {
			const floorGeom = new THREE.PlaneGeometry(width * 0.9, width * 0.9);
			const floorMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.1, side: THREE.DoubleSide });
			const floor = new THREE.Mesh(floorGeom, floorMat);
			floor.rotation.x = -Math.PI / 2;
			floor.position.y = f * 10;
			group.add(floor);
		}
	};
	
	const createPyramidTower = (THREE: any, group: any, height: number, width: number, color: number, altColor: number) => {
		const segments = 5;
		for (let i = 0; i < segments; i++) {
			const segHeight = height / segments;
			const segWidth = width * (1 - i * 0.18);
			
			// Wireframe segment
			const geometry = new THREE.BoxGeometry(segWidth, segHeight, segWidth, 1, 2, 1);
			const wireframeMat = new THREE.MeshBasicMaterial({ 
				color: i % 2 === 0 ? color : altColor, 
				wireframe: true, 
				transparent: true, 
				opacity: 0.5 
			});
			const wireframe = new THREE.Mesh(geometry, wireframeMat);
			wireframe.position.y = i * segHeight + segHeight / 2;
			group.add(wireframe);
			
			// Glowing edges
			const edges = new THREE.EdgesGeometry(new THREE.BoxGeometry(segWidth, segHeight, segWidth));
			const edgeLine = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ 
				color: i % 2 === 0 ? color : altColor, 
				transparent: true, 
				opacity: 0.8 
			}));
			edgeLine.position.y = i * segHeight + segHeight / 2;
			group.add(edgeLine);
		}
		
		// Vertical accent lines
		for (let corner = 0; corner < 4; corner++) {
			const angle = (corner / 4) * Math.PI * 2 + Math.PI / 4;
			const lineGeom = new THREE.BufferGeometry().setFromPoints([
				new THREE.Vector3(Math.cos(angle) * width * 0.7, 0, Math.sin(angle) * width * 0.7),
				new THREE.Vector3(Math.cos(angle) * width * 0.2, height, Math.sin(angle) * width * 0.2)
			]);
			const lineMat = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.7 });
			group.add(new THREE.Line(lineGeom, lineMat));
		}
	};
	
	const createCylinderTower = (THREE: any, group: any, height: number, width: number, color: number) => {
		// Outer wireframe cylinder
		const geometry = new THREE.CylinderGeometry(width / 2, width / 2, height, 16, 6, true);
		const wireframeMat = new THREE.MeshBasicMaterial({ color, wireframe: true, transparent: true, opacity: 0.4 });
		const wireframe = new THREE.Mesh(geometry, wireframeMat);
		wireframe.position.y = height / 2;
		group.add(wireframe);
		
		// Glowing edge rings at top and bottom
		const topRingGeom = new THREE.RingGeometry(width / 2 - 0.1, width / 2, 16);
		const ringMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.8, side: THREE.DoubleSide });
		const topRing = new THREE.Mesh(topRingGeom, ringMat);
		topRing.rotation.x = -Math.PI / 2;
		topRing.position.y = height;
		group.add(topRing);
		
		const bottomRing = new THREE.Mesh(topRingGeom.clone(), ringMat);
		bottomRing.rotation.x = -Math.PI / 2;
		group.add(bottomRing);
		
		// Inner core
		const innerGeometry = new THREE.CylinderGeometry(width / 3, width / 3, height * 0.9, 8, 4, true);
		const innerMat = new THREE.MeshBasicMaterial({ color, wireframe: true, transparent: true, opacity: 0.6 });
		const inner = new THREE.Mesh(innerGeometry, innerMat);
		inner.position.y = height / 2;
		group.add(inner);
		
		// Vertical glowing lines
		for (let i = 0; i < 8; i++) {
			const angle = (i / 8) * Math.PI * 2;
			const lineGeom = new THREE.BufferGeometry().setFromPoints([
				new THREE.Vector3(Math.cos(angle) * width / 2, 0, Math.sin(angle) * width / 2),
				new THREE.Vector3(Math.cos(angle) * width / 2, height, Math.sin(angle) * width / 2)
			]);
			const lineMat = new THREE.LineBasicMaterial({ color, transparent: true, opacity: i % 2 === 0 ? 0.9 : 0.4 });
			group.add(new THREE.Line(lineGeom, lineMat));
		}
	};
	
	const createStackedTower = (THREE: any, group: any, height: number, width: number, color: number, altColor: number, seed: number) => {
		const blocks = Math.floor(seededRandom(seed + 500) * 4) + 3;
		let currentY = 0;
		
		for (let i = 0; i < blocks; i++) {
			const blockHeight = height / blocks + (seededRandom(seed + i * 77) - 0.5) * 5;
			const blockWidth = width * (0.7 + seededRandom(seed + i * 88) * 0.6);
			const blockColor = i % 2 === 0 ? color : altColor;
			
			// Wireframe block
			const geometry = new THREE.BoxGeometry(blockWidth, blockHeight, blockWidth, 1, 2, 1);
			const wireframeMat = new THREE.MeshBasicMaterial({ color: blockColor, wireframe: true, transparent: true, opacity: 0.5 });
			const wireframe = new THREE.Mesh(geometry, wireframeMat);
			wireframe.position.y = currentY + blockHeight / 2;
			wireframe.rotation.y = seededRandom(seed + i * 99) * Math.PI / 4;
			group.add(wireframe);
			
			// Glowing edges
			const edges = new THREE.EdgesGeometry(new THREE.BoxGeometry(blockWidth, blockHeight, blockWidth));
			const edgeLine = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: blockColor, transparent: true, opacity: 0.8 }));
			edgeLine.position.y = currentY + blockHeight / 2;
			edgeLine.rotation.y = wireframe.rotation.y;
			group.add(edgeLine);
			
			currentY += blockHeight;
		}
		
		// Central spine
		const spineGeom = new THREE.BufferGeometry().setFromPoints([
			new THREE.Vector3(0, 0, 0),
			new THREE.Vector3(0, currentY, 0)
		]);
		const spineMat = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.6 });
		group.add(new THREE.Line(spineGeom, spineMat));
	};
	
	const createSpireTower = (THREE: any, group: any, height: number, width: number, color: number, altColor: number) => {
		// Base platform with wireframe
		const baseGeometry = new THREE.BoxGeometry(width * 1.5, height * 0.25, width * 1.5, 2, 2, 2);
		const baseMat = new THREE.MeshBasicMaterial({ color, wireframe: true, transparent: true, opacity: 0.5 });
		const base = new THREE.Mesh(baseGeometry, baseMat);
		base.position.y = height * 0.125;
		group.add(base);
		
		// Base edges
		const baseEdges = new THREE.EdgesGeometry(new THREE.BoxGeometry(width * 1.5, height * 0.25, width * 1.5));
		const baseEdgeLine = new THREE.LineSegments(baseEdges, new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.9 }));
		baseEdgeLine.position.y = height * 0.125;
		group.add(baseEdgeLine);
		
		// Spire wireframe
		const spireGeometry = new THREE.ConeGeometry(width / 2, height * 0.75, 8, 4, true);
		const spireMat = new THREE.MeshBasicMaterial({ color: altColor, wireframe: true, transparent: true, opacity: 0.5 });
		const spire = new THREE.Mesh(spireGeometry, spireMat);
		spire.position.y = height * 0.25 + height * 0.375;
		group.add(spire);
		
		// Spire edges
		const spireEdges = new THREE.EdgesGeometry(new THREE.ConeGeometry(width / 2, height * 0.75, 8));
		const spireEdgeLine = new THREE.LineSegments(spireEdges, new THREE.LineBasicMaterial({ color: altColor, transparent: true, opacity: 0.9 }));
		spireEdgeLine.position.y = height * 0.25 + height * 0.375;
		group.add(spireEdgeLine);
		
		// Antenna at top
		const antennaGeom = new THREE.BufferGeometry().setFromPoints([
			new THREE.Vector3(0, height, 0),
			new THREE.Vector3(0, height + 5, 0)
		]);
		const antennaMat = new THREE.LineBasicMaterial({ color: altColor, transparent: true, opacity: 0.9 });
		group.add(new THREE.Line(antennaGeom, antennaMat));
		
		// Cross bars on antenna
		for (let i = 0; i < 3; i++) {
			const barY = height + 1 + i * 1.5;
			const barWidth = 1.5 - i * 0.4;
			const barGeom = new THREE.BufferGeometry().setFromPoints([
				new THREE.Vector3(-barWidth, barY, 0),
				new THREE.Vector3(barWidth, barY, 0)
			]);
			group.add(new THREE.Line(barGeom, antennaMat));
		}
	};
	
	const updateChunks = () => {
		if (!threeRef) return;
		
		const camChunkX = Math.floor(cameraWorldPos.x / CHUNK_SIZE);
		const camChunkZ = Math.floor(cameraWorldPos.z / CHUNK_SIZE);
		
		const neededChunks = new Set<string>();
		
		// Determine which chunks should be loaded
		for (let dx = -RENDER_DISTANCE; dx <= RENDER_DISTANCE; dx++) {
			for (let dz = -RENDER_DISTANCE; dz <= RENDER_DISTANCE; dz++) {
				const cx = camChunkX + dx;
				const cz = camChunkZ + dz;
				neededChunks.add(getChunkKey(cx, cz));
			}
		}
		
		// Unload chunks that are too far
		for (const [key, chunk] of loadedChunks) {
			if (!neededChunks.has(key)) {
				scene.remove(chunk);
				// Clean up buildings array
				if (chunk.userData.buildings) {
					chunk.userData.buildings.forEach((b: any) => {
						const idx = buildings.indexOf(b);
						if (idx > -1) buildings.splice(idx, 1);
					});
				}
				loadedChunks.delete(key);
			}
		}
		
		// Load new chunks
		for (const key of neededChunks) {
			if (!loadedChunks.has(key)) {
				const [cx, cz] = key.split(',').map(Number);
				const chunk = generateChunk(cx, cz);
				if (chunk) {
					scene.add(chunk);
					loadedChunks.set(key, chunk);
				}
			}
		}
	};
	
	const createDataHighway = (THREE: any, from: any, to: any): { group: any } | null => {
		if (!from?.userData?.height || !to?.userData?.height) return null;
		
		const startY = from.userData.height * 0.7;
		const endY = to.userData.height * 0.7;
		
		// Get world positions
		const fromPos = from.position;
		const toPos = to.position;
		
		const curve = new THREE.QuadraticBezierCurve3(
			new THREE.Vector3(fromPos.x, startY, fromPos.z),
			new THREE.Vector3(
				(fromPos.x + toPos.x) / 2,
				Math.max(startY, endY) + 15,
				(fromPos.z + toPos.z) / 2
			),
			new THREE.Vector3(toPos.x, endY, toPos.z)
		);
		
		const highwayGroup = new THREE.Group();
		
		const points = curve.getPoints(30);
		const geometry = new THREE.BufferGeometry().setFromPoints(points);
		const material = new THREE.LineBasicMaterial({
			color: 0x00ffff,
			transparent: true,
			opacity: 0.3
		});
		
		const highway = new THREE.Line(geometry, material);
		highwayGroup.add(highway);
		connections.push(highway);
		
		// Data packet traveling along highway
		const packetGeometry = new THREE.SphereGeometry(0.4, 8, 8);
		const packetMaterial = new THREE.MeshBasicMaterial({
			color: 0xff00ff,
			transparent: true,
			opacity: 0.9
		});
		const packet = new THREE.Mesh(packetGeometry, packetMaterial);
		packet.userData = { curve, progress: Math.random(), speed: 0.003 + Math.random() * 0.004 };
		highwayGroup.add(packet);
		dataStreams.push(packet);
		
		return { group: highwayGroup };
	};
	
	let lastChunkUpdate = 0;
	
	const animate = (THREE: any) => {
		animationId = requestAnimationFrame(() => animate(THREE));
		
		const time = Date.now() * 0.001;
		
		// Update equalizer visualization
		updateEqualizer();
		
		// Apply joystick movement for mobile
		applyJoystickMovement();
		
		// Update camera world position for chunk loading
		cameraWorldPos.x += (cameraTarget.x - cameraWorldPos.x) * 0.03;
		cameraWorldPos.z += (cameraTarget.z - cameraWorldPos.z) * 0.03;
		
		// Camera follows world position
		camera.position.x = cameraWorldPos.x;
		camera.position.y += (cameraTarget.y - camera.position.y) * 0.03;
		camera.position.z = cameraWorldPos.z + zoom;
		
		// Look at point ahead of camera
		camera.lookAt(cameraWorldPos.x, cameraTarget.y * 0.5, cameraWorldPos.z - 20);
		
		// Update chunks periodically (not every frame for performance)
		if (time - lastChunkUpdate > 0.5) {
			updateChunks();
			lastChunkUpdate = time;
			
			// Check if we need to lazy load more chats
			// Trigger when camera approaches the end of the timeline
			const distanceToEnd = timelineEnd - cameraWorldPos.z;
			if (distanceToEnd < LOAD_TRIGGER_DISTANCE && hasMoreChats && !isLoadingMoreChats) {
				loadMoreChats();
			}
		}
		
		// Animate buildings
		buildings.forEach((building: any, index: number) => {
			// Beacon pulse
			const beacon = building.children.find((c: any) => c.geometry?.type === 'SphereGeometry');
			if (beacon) {
				const pulse = Math.sin(time * 3 + index) * 0.3 + 0.7;
				beacon.material.opacity = pulse;
			}
			
			// Rotate data rings
			building.children.forEach((child: any) => {
				if (child.userData.rotationSpeed) {
					child.rotation.z += child.userData.rotationSpeed;
				}
			});
		});
		
		// Animate folder nodes
		folderNodes.forEach((folderNode: any, folderId: string) => {
			// Gentle floating motion
			const baseY = 60;
			folderNode.position.y = baseY + Math.sin(time * 1.5 + folderId.length) * 2;
			
			// Rotate the ring around the folder
			folderNode.children.forEach((child: any) => {
				if (child.userData.rotationSpeed) {
					child.rotation.z += child.userData.rotationSpeed;
				}
			});
			
			// Pulse the hexagon opacity
			const hexMesh = folderNode.children.find((c: any) => c.geometry?.type === 'CylinderGeometry');
			if (hexMesh) {
				const pulse = Math.sin(time * 2 + folderId.length * 0.5) * 0.2 + 0.7;
				hexMesh.material.opacity = pulse;
			}
		});
		
		// Make Model Hub follow camera
		if (modelHubGroup) {
			modelHubGroup.position.copy(camera.position);
			modelHubGroup.rotation.copy(camera.rotation);
		}
		
		// Animate Model Hub orbs
		modelHub.forEach((orb: any, modelName: string) => {
			if (orb.userData?.isModel) {
				// Subtle floating bob motion
				const baseY = orb.userData.baseY;
				orb.position.y = baseY + Math.sin(time * 2 + modelName.length) * 0.15;
				
				// Rotate orb
				orb.rotation.y += orb.userData.rotationSpeed;
				orb.rotation.x = Math.sin(time * 0.5) * 0.1;
				
				// Rotate orbit ring
				if (orb.userData.orbitRing) {
					orb.userData.orbitRing.rotation.z += 0.02;
				}
				
				// Highlight if hovered
				if (orb === hoveredModel) {
					orb.scale.setScalar(1.4);
					orb.material.opacity = 1;
				} else {
					orb.scale.setScalar(1);
					orb.material.opacity = 0.7;
				}
			}
		});
		
		// Animate data packets along highways
		dataStreams.forEach((packet: any) => {
			if (!packet.userData?.curve) return;
			packet.userData.progress += packet.userData.speed;
			if (packet.userData.progress > 1) {
				packet.userData.progress = 0;
			}
			try {
				const point = packet.userData.curve.getPoint(packet.userData.progress);
				packet.position.copy(point);
			} catch (e) {
				// Curve may be invalid if chunk was unloaded
			}
			
			// Pulse effect
			const scale = 0.8 + Math.sin(time * 10) * 0.2;
			packet.scale.setScalar(scale);
		});
		
		// Animate flying particles - grid-following network packets
		if (scene.userData.particles) {
			const positions = scene.userData.particles.geometry.attributes.position.array;
			const velocities = scene.userData.particles.userData.velocities;
			const packetData = scene.userData.particles.userData.packetData;
			
			// Get audio frequency data
			const { bass } = getFrequencyBands();
			const audioLevel = getAudioLevel();
			
			// Audio affects particle appearance - keep them small!
			if (audioEnabled && audioLevel > 0.01) {
				scene.userData.particles.material.size = 0.4 + bass * 0.3; // Much smaller
				scene.userData.particles.material.opacity = 0.7 + audioLevel * 0.3;
			} else {
				scene.userData.particles.material.size = 0.5;
				scene.userData.particles.material.opacity = 0.9;
			}
			
			for (let i = 0; i < positions.length / 3; i++) {
				const packet = packetData[i];
				
				// Move along grid line
				positions[i * 3] += velocities[i * 3];
				positions[i * 3 + 1] += velocities[i * 3 + 1];
				positions[i * 3 + 2] += velocities[i * 3 + 2];
				
				// Audio mode - only 50% of particles (even indices) react to audio
				const isAudioReactive = i % 2 === 0;
				
				if (audioEnabled && audioLevel > 0.02 && isAudioReactive) {
					// Assign each particle to an EQ band (16 bands)
					const eqBand = i % 16;
					const eqValue = eqBars[eqBand] || 0;
					
					// Particles rise like energy streams - smooth wave motion
					const wavePhase = time * 4 + i * 0.3;
					const baseRise = eqValue * 25; // Max rise based on EQ
					const waveOffset = Math.sin(wavePhase) * (3 + eqValue * 8);
					
					// Gentle upward drift with wave motion
					positions[i * 3 + 1] = 1 + baseRise + waveOffset;
					
					// Subtle horizontal sway synced to audio
					const swayAmount = eqValue * 2;
					positions[i * 3] += Math.sin(wavePhase * 0.7) * swayAmount * 0.1;
					positions[i * 3 + 2] += Math.cos(wavePhase * 0.5) * swayAmount * 0.1;
					
					// Speed boost based on overall audio level
					const speedMult = 1 + bass * 3;
					positions[i * 3] += velocities[i * 3] * speedMult;
					positions[i * 3 + 2] += velocities[i * 3 + 2] * speedMult;
				} else {
					// Stay on grid - low to ground
					positions[i * 3 + 1] = 0.5 + Math.sin(time * 2 + i * 0.1) * 0.3;
				}
				
				// Wrap around camera position
				const relX = positions[i * 3] - cameraWorldPos.x;
				const relZ = positions[i * 3 + 2] - cameraWorldPos.z;
				
				if (Math.abs(relX) > 150) {
					positions[i * 3] = cameraWorldPos.x - relX * 0.9;
				}
				if (Math.abs(relZ) > 150) {
					positions[i * 3 + 2] = cameraWorldPos.z - relZ * 0.9;
				}
			}
			scene.userData.particles.geometry.attributes.position.needsUpdate = true;
		}
		
		// Sweep spotlights around camera
		if (scene.userData.spotlights) {
			scene.userData.spotlights[0].position.x = cameraWorldPos.x + Math.sin(time * 0.3) * 80;
			scene.userData.spotlights[0].position.z = cameraWorldPos.z + Math.cos(time * 0.3) * 80;
			scene.userData.spotlights[1].position.x = cameraWorldPos.x + Math.sin(time * 0.3 + Math.PI) * 80;
			scene.userData.spotlights[1].position.z = cameraWorldPos.z + Math.cos(time * 0.3 + Math.PI) * 80;
		}
		
		// Audio-reactive buildings - pulse to the beat
		if (audioEnabled) {
			const { bass, mid } = getFrequencyBands();
			chatBuildings.forEach((building: any) => {
				if (building.userData?.isChat) {
					// Scale buildings slightly with bass
					const baseScale = 1;
					const audioScale = baseScale + bass * 0.15;
					building.scale.setScalar(audioScale);
					
					// Pulse beacon brightness with mid frequencies
					building.children.forEach((child: any) => {
						if (child.material && child.geometry?.type === 'SphereGeometry') {
							child.material.opacity = 0.5 + mid * 0.5;
						}
					});
				}
			});
		}
		
		// Warp speed effect animation
		if (isWarping && scene.userData.warpGroup) {
			warpSpeed = Math.min(warpSpeed + 0.1, 5);
			
			warpLines.forEach((line: any) => {
				line.position.z += warpSpeed * line.userData.speed;
				
				// Reset lines that pass the camera
				if (line.position.z > 30) {
					line.position.z = line.userData.baseZ - 50;
				}
				
				// Stretch lines based on speed
				line.scale.z = 1 + warpSpeed * 0.5;
			});
			
			// Position warp group relative to camera
			scene.userData.warpGroup.position.set(
				camera.position.x,
				camera.position.y,
				camera.position.z - 30
			);
		}
		
		renderer.render(scene, camera);
	};
	
	const CAMERA_STORAGE_KEY = 'pigateway-camera-id';
	
	const enumerateVideoDevices = async () => {
		const devices = await navigator.mediaDevices.enumerateDevices();
		videoDevices = devices.filter(device => device.kind === 'videoinput');
		
		// Try to load saved camera preference
		const savedCameraId = localStorage.getItem(CAMERA_STORAGE_KEY);
		if (savedCameraId && videoDevices.some(d => d.deviceId === savedCameraId)) {
			selectedDeviceId = savedCameraId;
		} else if (!selectedDeviceId && videoDevices.length > 0) {
			selectedDeviceId = videoDevices[0].deviceId;
		}
	};
	
	const switchCamera = async (deviceId: string) => {
		if (!gestureController) return;
		
		selectedDeviceId = deviceId;
		showDeviceMenu = false;
		
		// Save camera preference
		localStorage.setItem(CAMERA_STORAGE_KEY, deviceId);
		
		// Restart camera with new device
		gestureController.stopCamera();
		await gestureController.startCamera(deviceId);
	};
	
	let faceMeshGroup: any = null;
	let faceLandmarkPoints: any[] = [];
	let faceMeshLines: any = null;
	
	// Hand mesh state
	let handMeshGroups: any[] = [null, null]; // Up to 2 hands
	let handLandmarkPoints: any[][] = [[], []];
	let handMeshLines: any[] = [null, null];
	
	// Hand connections (MediaPipe hand landmarks)
	const HAND_CONNECTIONS = [
		// Thumb
		[0, 1], [1, 2], [2, 3], [3, 4],
		// Index finger
		[0, 5], [5, 6], [6, 7], [7, 8],
		// Middle finger
		[0, 9], [9, 10], [10, 11], [11, 12],
		// Ring finger
		[0, 13], [13, 14], [14, 15], [15, 16],
		// Pinky
		[0, 17], [17, 18], [18, 19], [19, 20],
		// Palm
		[5, 9], [9, 13], [13, 17]
	];
	
	const createHandMesh = (THREE: any, handIndex: number) => {
		if (handMeshGroups[handIndex]) {
			// Remove from parent (scene or faceMeshGroup)
			if (handMeshGroups[handIndex].parent) {
				handMeshGroups[handIndex].parent.remove(handMeshGroups[handIndex]);
			}
		}
		
		const handGroup = new THREE.Group();
		handGroup.userData.isHandMesh = true;
		
		// Create 21 landmark points for hand
		const pointGeometry = new THREE.SphereGeometry(0.06, 6, 6);
		const pointMaterial = new THREE.MeshBasicMaterial({ 
			color: handIndex === 0 ? 0x00ff88 : 0xff8800, // Green for left, orange for right
			transparent: true, 
			opacity: 1.0 
		});
		
		const points: any[] = [];
		for (let i = 0; i < 21; i++) {
			const point = new THREE.Mesh(pointGeometry, pointMaterial.clone());
			
			// Add glow
			const glowGeometry = new THREE.SphereGeometry(0.1, 4, 4);
			const glowMaterial = new THREE.MeshBasicMaterial({
				color: handIndex === 0 ? 0x00ff88 : 0xff8800,
				transparent: true,
				opacity: 0.2
			});
			const glow = new THREE.Mesh(glowGeometry, glowMaterial);
			point.add(glow);
			point.userData.glow = glow;
			
			points.push(point);
			handGroup.add(point);
		}
		
		handLandmarkPoints[handIndex] = points;
		
		// Create line geometry for hand connections
		const lineMaterial = new THREE.LineBasicMaterial({
			color: handIndex === 0 ? 0x00ff88 : 0xff8800,
			transparent: true,
			opacity: 0.9
		});
		
		const lineGeometry = new THREE.BufferGeometry();
		const lines = new THREE.LineSegments(lineGeometry, lineMaterial);
		lines.frustumCulled = false;
		handGroup.add(lines);
		handMeshLines[handIndex] = lines;
		
		handMeshGroups[handIndex] = handGroup;
		scene.add(handGroup);
	};
	
	const updateHandMesh = (landmarks: any[], handednesses: any[]) => {
		if (!threeRef || !camera) return;
		
		const THREE = threeRef;
		
		// Track which hands are currently detected
		const detectedHands = new Set<number>();
		
		// Update each detected hand
		for (let h = 0; h < Math.min(landmarks.length, 2); h++) {
			const handLandmarks = landmarks[h];
			// Use loop index directly - simpler and more reliable
			const handIndex = h;
			detectedHands.add(handIndex);
			
			// Create hand mesh if it doesn't exist
			if (!handMeshGroups[handIndex]) {
				createHandMesh(THREE, handIndex);
			}
			
			const handGroup = handMeshGroups[handIndex];
			const points = handLandmarkPoints[handIndex];
			
			// Re-add to scene if it was removed
			if (!handGroup.parent) {
				scene.add(handGroup);
			}
			
			// Make hand follow camera (same as face)
			handGroup.position.copy(camera.position);
			handGroup.rotation.copy(camera.rotation);
			
			// Position hand in camera space - beside the face
			// Face is at X=22, so put hands right next to it
			const handScale = 10;
			const offsetX = handIndex === 0 ? 20 : 24; // Very tight to face (face at 22)
			const offsetY = 10; // Same height as face
			const offsetZ = -35; // Same depth as face
			
			// Update point positions - position hands facing the user (palm toward camera)
			for (let i = 0; i < Math.min(handLandmarks.length, points.length); i++) {
				const lm = handLandmarks[i];
				const point = points[i];
				
				// No X mirror - MediaPipe already provides mirrored view
				// Negate Z so palm faces toward user
				point.position.set(
					(lm.x - 0.5) * handScale + offsetX,
					-(lm.y - 0.5) * handScale + offsetY,
					-lm.z * 10 + offsetZ // Negate Z and increase scale for depth
				);
				
				// Color fingertips differently
				const isFingertip = [4, 8, 12, 16, 20].includes(i);
				const isThumb = i >= 1 && i <= 4;
				
				if (isFingertip) {
					point.material.color.setHex(0xff00ff); // Magenta fingertips
					if (point.userData.glow) point.userData.glow.material.color.setHex(0xff00ff);
				} else if (isThumb) {
					point.material.color.setHex(0xffff00); // Yellow thumb
					if (point.userData.glow) point.userData.glow.material.color.setHex(0xffff00);
				} else {
					const baseColor = handIndex === 0 ? 0x00ff88 : 0xff8800;
					point.material.color.setHex(baseColor);
					if (point.userData.glow) point.userData.glow.material.color.setHex(baseColor);
				}
			}
			
			// Update lines
			const lines = handMeshLines[handIndex];
			if (lines) {
				const linePoints: any[] = [];
				
				for (const [idx1, idx2] of HAND_CONNECTIONS) {
					const p1 = points[idx1];
					const p2 = points[idx2];
					
					if (p1 && p2) {
						linePoints.push(new THREE.Vector3(p1.position.x, p1.position.y, p1.position.z));
						linePoints.push(new THREE.Vector3(p2.position.x, p2.position.y, p2.position.z));
					}
				}
				
				if (lines.geometry) lines.geometry.dispose();
				lines.geometry = new THREE.BufferGeometry().setFromPoints(linePoints);
			}
		}
		
		// Remove hands that aren't detected from the scene
		for (let h = 0; h < 2; h++) {
			if (handMeshGroups[h] && !detectedHands.has(h)) {
				if (handMeshGroups[h].parent) {
					handMeshGroups[h].parent.remove(handMeshGroups[h]);
				}
			}
		}
	};
	
	const createFaceMesh = (THREE: any) => {
		if (faceMeshGroup) {
			scene.remove(faceMeshGroup);
		}
		
		faceMeshGroup = new THREE.Group();
		faceMeshGroup.userData.isFaceMesh = true;
		
		// Create high-fidelity points for face landmarks (468 points in MediaPipe face mesh)
		// Smaller, smoother spheres for cleaner look
		const pointGeometry = new THREE.SphereGeometry(0.08, 8, 8);
		const pointMaterial = new THREE.MeshBasicMaterial({ 
			color: 0x00ffff, 
			transparent: true, 
			opacity: 1.0 
		});
		
		// Create 468 landmark points with glow effect
		for (let i = 0; i < 468; i++) {
			const point = new THREE.Mesh(pointGeometry, pointMaterial.clone());
			
			// Add outer glow sphere
			const glowGeometry = new THREE.SphereGeometry(0.12, 6, 6);
			const glowMaterial = new THREE.MeshBasicMaterial({
				color: 0x00ffff,
				transparent: true,
				opacity: 0.25
			});
			const glow = new THREE.Mesh(glowGeometry, glowMaterial);
			point.add(glow);
			point.userData.glow = glow;
			
			faceLandmarkPoints.push(point);
			faceMeshGroup.add(point);
		}
		
		// Create line geometry for face mesh connections
		// Will be populated in updateFaceMesh
		const lineMaterial = new THREE.LineBasicMaterial({
			color: 0x00ffff,
			transparent: true,
			opacity: 0.6,
			linewidth: 2
		});
		
		// Create empty geometry - will be filled with actual positions in update
		const lineGeometry = new THREE.BufferGeometry();
		faceMeshLines = new THREE.LineSegments(lineGeometry, lineMaterial);
		faceMeshLines.frustumCulled = false; // Always render
		faceMeshGroup.add(faceMeshLines);
		
		scene.add(faceMeshGroup);
	};
	
	// Face mesh tessellation connections (simplified key edges)
	const FACE_MESH_CONNECTIONS = [
		// Face oval
		[10, 338], [338, 297], [297, 332], [332, 284], [284, 251], [251, 389], [389, 356], [356, 454],
		[454, 323], [323, 361], [361, 288], [288, 397], [397, 365], [365, 379], [379, 378], [378, 400],
		[400, 377], [377, 152], [152, 148], [148, 176], [176, 149], [149, 150], [150, 136], [136, 172],
		[172, 58], [58, 132], [132, 93], [93, 234], [234, 127], [127, 162], [162, 21], [21, 54],
		[54, 103], [103, 67], [67, 109], [109, 10],
		// Left eye
		[33, 7], [7, 163], [163, 144], [144, 145], [145, 153], [153, 154], [154, 155], [155, 133],
		[133, 173], [173, 157], [157, 158], [158, 159], [159, 160], [160, 161], [161, 246], [246, 33],
		// Right eye
		[362, 382], [382, 381], [381, 380], [380, 374], [374, 373], [373, 390], [390, 249], [249, 263],
		[263, 466], [466, 388], [388, 387], [387, 386], [386, 385], [385, 384], [384, 398], [398, 362],
		// Lips outer
		[61, 146], [146, 91], [91, 181], [181, 84], [84, 17], [17, 314], [314, 405], [405, 321],
		[321, 375], [375, 291], [291, 409], [409, 270], [270, 269], [269, 267], [267, 0], [0, 37],
		[37, 39], [39, 40], [40, 185], [185, 61],
		// Lips inner
		[78, 95], [95, 88], [88, 178], [178, 87], [87, 14], [14, 317], [317, 402], [402, 318],
		[318, 324], [324, 308], [308, 415], [415, 310], [310, 311], [311, 312], [312, 13], [13, 82],
		[82, 81], [81, 80], [80, 191], [191, 78],
		// Nose
		[168, 6], [6, 197], [197, 195], [195, 5], [5, 4], [4, 1], [1, 19], [19, 94], [94, 2],
		// Left eyebrow
		[46, 53], [53, 52], [52, 65], [65, 55], [55, 107], [107, 66], [66, 105], [105, 63], [63, 70],
		// Right eyebrow
		[276, 283], [283, 282], [282, 295], [295, 285], [285, 336], [336, 296], [296, 334], [334, 293], [293, 300]
	];
	
	const updateFaceMesh = (landmarks: any[], blendShapes: any[]) => {
		if (!faceMeshGroup || !threeRef || !camera || landmarks.length === 0) return;
		
		const faceLandmarks = landmarks[0]; // First face
		
		// Make face mesh follow camera (like model nodes)
		// Position in top-right corner of view, fixed relative to camera
		faceMeshGroup.position.copy(camera.position);
		faceMeshGroup.rotation.copy(camera.rotation);
		
		// Update each landmark point position - positioned in top-right corner
		for (let i = 0; i < Math.min(faceLandmarks.length, faceLandmarkPoints.length); i++) {
			const lm = faceLandmarks[i];
			const point = faceLandmarkPoints[i];
			
			// Scale and offset landmarks (they come as 0-1 normalized)
			// Position relative to camera view: right (+X local), up (+Y local), forward (-Z local)
			const faceScale = 25; // Bigger face
			const offsetX = 22;   // Right side of view
			const offsetY = 12;   // Top of view
			const offsetZ = -35;  // In front of camera
			
			point.position.set(
				(lm.x - 0.5) * faceScale + offsetX,
				-(lm.y - 0.5) * faceScale + offsetY,
				lm.z * 5 + offsetZ
			);
			
			// Color key points differently with matching glow
			const isEye = (i >= 33 && i <= 133) || (i >= 362 && i <= 398);
			const isLips = (i >= 61 && i <= 95) || (i >= 146 && i <= 178) || (i >= 291 && i <= 325) || (i >= 375 && i <= 409);
			const isNose = i >= 1 && i <= 19;
			const isBrow = (i >= 46 && i <= 55) || (i >= 276 && i <= 285);
			const isContour = (i >= 234 && i <= 261) || (i >= 454 && i <= 473);
			
			let color = 0x00ffff; // Default cyan
			if (isEye) {
				color = 0xff00ff; // Magenta for eyes
			} else if (isLips) {
				color = 0xff0066; // Pink for lips
			} else if (isNose) {
				color = 0xffff00; // Yellow for nose
			} else if (isBrow) {
				color = 0xff8800; // Orange for brows
			} else if (isContour) {
				color = 0x00ff88; // Green for face contour
			}
			
			point.material.color.setHex(color);
			// Update glow color to match
			if (point.userData.glow) {
				point.userData.glow.material.color.setHex(color);
			}
		}
		
		// Update line positions to connect points
		if (faceMeshLines) {
			const THREE = threeRef;
			const linePoints: any[] = [];
			
			for (let i = 0; i < FACE_MESH_CONNECTIONS.length; i++) {
				const [idx1, idx2] = FACE_MESH_CONNECTIONS[i];
				const p1 = faceLandmarkPoints[idx1];
				const p2 = faceLandmarkPoints[idx2];
				
				if (p1 && p2) {
					linePoints.push(new THREE.Vector3(p1.position.x, p1.position.y, p1.position.z));
					linePoints.push(new THREE.Vector3(p2.position.x, p2.position.y, p2.position.z));
				}
			}
			
			// Dispose old geometry and create new
			if (faceMeshLines.geometry) {
				faceMeshLines.geometry.dispose();
			}
			faceMeshLines.geometry = new THREE.BufferGeometry().setFromPoints(linePoints);
		}
		
		// Apply blend shapes for expression (e.g., mouth open, eyebrow raise)
		if (blendShapes.length > 0) {
			const mouthOpen = blendShapes.find((b: any) => b.categoryName === 'jawOpen')?.score || 0;
			const eyeBrowUp = blendShapes.find((b: any) => b.categoryName === 'browOuterUpLeft')?.score || 0;
			
			// Subtle scale pulse based on expressions
			const baseScale = 1;
			const expressionScale = baseScale + mouthOpen * 0.1 + eyeBrowUp * 0.05;
			// Don't reset scale - it's handled by camera following
		}
	};
	
	const initGestureControl = async () => {
		await enumerateVideoDevices();
		
		gestureController = new MediaPipeGestureController();
		await gestureController.initialize(videoElement, gestureCanvas);
		await gestureController.startCamera(selectedDeviceId || undefined);
		
		// Create and setup face mesh and hand tracking
		if (threeRef) {
			createFaceMesh(threeRef);
			gestureController.onFaceLandmarks(updateFaceMesh);
			gestureController.onHandLandmarks(updateHandMesh);
		}
		
		// ✊ FIST = TURBO forward into the past (older chats)
		gestureController.on('Closed_Fist', () => {
			currentGesture = '✊ TURBO → Past!';
			cameraTarget.z += 50; // Forward along timeline (toward older)
		});
		
		// ✋ OPEN PALM = HALT & select nearest chat
		gestureController.on('Open_Palm', () => {
			currentGesture = '✋ HALT - Scanning...';
			flySpeed = 0;
			// Auto-select nearest chat when halting
			const chatBuildingArray = Array.from(chatBuildings.values());
			let nearest = null;
			let nearestDist = Infinity;
			for (const building of chatBuildingArray) {
				const dx = building.position.x - cameraWorldPos.x;
				const dz = building.position.z - cameraWorldPos.z;
				const dist = Math.sqrt(dx * dx + dz * dz);
				if (dist < nearestDist) {
					nearestDist = dist;
					nearest = building;
				}
			}
			if (nearest && nearestDist < 30) {
				selectedChatBuilding = nearest;
				currentGesture = `✋ LOCKED: ${nearest.userData.chatTitle}`;
			}
		});
		
		// ☝️ POINTING = Fly backward toward NOW (newer chats)
		gestureController.on('Pointing_Up', () => {
			currentGesture = '☝️ BACK ← Now!';
			cameraTarget.z -= 25; // Backward along timeline (toward newer)
		});
		
		// ✌️ VICTORY = Ascend for overview
		gestureController.on('Victory', () => {
			currentGesture = '✌️ OVERVIEW - Bird\'s eye!';
			cameraTarget.y = Math.min(120, cameraTarget.y + 15);
		});
		
		// 👎 THUMBS DOWN = Strafe to morning chats (left)
		gestureController.on('Thumb_Down', () => {
			currentGesture = '👎 ← Morning chats';
			cameraTarget.x -= 15;
		});
		
		// 👍 THUMBS UP = Strafe to evening chats (right)
		gestureController.on('Thumb_Up', () => {
			currentGesture = '👍 → Evening chats';
			cameraTarget.x += 15;
		});
		
		// 🤟 I LOVE YOU = Warp to next chat along timeline
		gestureController.on('ILoveYou', () => {
			const chatBuildingArray = Array.from(chatBuildings.values());
			if (chatBuildingArray.length > 0) {
				// Start warp effect
				startWarp();
				
				// Find next chat ahead on timeline
				const aheadChats = chatBuildingArray
					.filter(b => b.position.z > cameraWorldPos.z)
					.sort((a, b) => a.position.z - b.position.z);
				
				let target;
				if (aheadChats.length > 0) {
					target = aheadChats[0]; // Next chat ahead
					currentGesture = `🤟 WARP → ${target.userData.chatTitle}`;
				} else {
					// Wrap to beginning if at end
					const sorted = [...chatBuildingArray].sort((a, b) => a.position.z - b.position.z);
					target = sorted[0];
					currentGesture = `🤟 WARP ↺ ${target.userData.chatTitle}`;
				}
				
				selectedChatBuilding = target;
				cameraTarget.x = target.position.x;
				cameraTarget.z = target.position.z - 10; // Position behind the chat
				cameraTarget.y = Math.max(20, target.userData.height * 0.8);
				zoom = 25;
				
				// Stop warp after arriving
				setTimeout(() => stopWarp(), 800);
			}
		});
	};
	
	// Open selected chat
	const openSelectedChat = () => {
		if (selectedChatBuilding?.userData?.chatId) {
			const chatIdToOpen = selectedChatBuilding.userData.chatId;
			onClose();
			goto(`/c/${chatIdToOpen}`);
		}
	};
	
	const toggleGestureMode = async () => {
		if (!gestureMode) {
			// Turning ON gesture mode
			try {
				// Request camera permission first
				await navigator.mediaDevices.getUserMedia({ video: true });
				gestureMode = true;
				
				// Wait for video element to be rendered
				await tick();
				
				if (!videoElement || !gestureCanvas) {
					throw new Error('Video elements not ready');
				}
				
				await initGestureControl();
			} catch (error: unknown) {
				console.error('Failed to initialize gesture control:', error);
				const errorMessage = error instanceof Error ? error.message : 'Camera access denied';
				currentGesture = `Error: ${errorMessage}`;
				gestureMode = false;
				
				// Clear error after 3 seconds
				setTimeout(() => {
					if (!gestureMode) currentGesture = '';
				}, 3000);
			}
		} else {
			// Turning OFF gesture mode
			if (gestureController) {
				gestureController.dispose();
				gestureController = null;
			}
			
			// Remove face mesh from scene
			if (faceMeshGroup && scene) {
				scene.remove(faceMeshGroup);
				faceMeshGroup = null;
				faceLandmarkPoints = [];
			}
			
			gestureMode = false;
			currentGesture = '';
		}
	};
	
	// Audio reactivity functions
	let audioMode: 'off' | 'mic' | 'system' = 'off';
	let audioStream: MediaStream | null = null;
	
	const initAudioMic = async () => {
		try {
			// Create audio context
			audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
			audioAnalyzer = audioContext.createAnalyser();
			audioAnalyzer.fftSize = 256;
			audioAnalyzer.smoothingTimeConstant = 0.8;
			
			const bufferLength = audioAnalyzer.frequencyBinCount;
			audioDataArray = new Uint8Array(bufferLength);
			
			// Get microphone input
			audioStream = await navigator.mediaDevices.getUserMedia({ 
				audio: {
					echoCancellation: false,
					noiseSuppression: false,
					autoGainControl: false
				}
			});
			
			const source = audioContext.createMediaStreamSource(audioStream);
			source.connect(audioAnalyzer);
			
			audioEnabled = true;
			audioMode = 'mic';
			console.log('🎤 Microphone audio enabled');
		} catch (error) {
			console.error('Failed to initialize microphone audio:', error);
			audioEnabled = false;
			audioMode = 'off';
		}
	};
	
	const initAudioSystem = async () => {
		try {
			// Create audio context
			audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
			audioAnalyzer = audioContext.createAnalyser();
			audioAnalyzer.fftSize = 256;
			audioAnalyzer.smoothingTimeConstant = 0.8;
			
			const bufferLength = audioAnalyzer.frequencyBinCount;
			audioDataArray = new Uint8Array(bufferLength);
			
			// Get system audio via screen share (user must share a tab/window with audio)
			audioStream = await navigator.mediaDevices.getDisplayMedia({ 
				video: true, // Required but we won't use it
				audio: {
					echoCancellation: false,
					noiseSuppression: false,
					autoGainControl: false
				} as any
			});
			
			// Check if we got audio
			const audioTracks = audioStream.getAudioTracks();
			if (audioTracks.length === 0) {
				throw new Error('No audio track - make sure to share a tab with audio');
			}
			
			// Stop video track since we don't need it
			audioStream.getVideoTracks().forEach(track => track.stop());
			
			const source = audioContext.createMediaStreamSource(audioStream);
			source.connect(audioAnalyzer);
			
			audioEnabled = true;
			audioMode = 'system';
			console.log('🔊 System audio enabled');
		} catch (error) {
			console.error('Failed to initialize system audio:', error);
			audioEnabled = false;
			audioMode = 'off';
		}
	};
	
	const stopAudio = async () => {
		if (audioStream) {
			audioStream.getTracks().forEach(track => track.stop());
			audioStream = null;
		}
		if (audioContext) {
			await audioContext.close();
			audioContext = null;
			audioAnalyzer = null;
			audioDataArray = null;
		}
		audioEnabled = false;
		audioMode = 'off';
	};
	
	const cycleAudioMode = async () => {
		// Cycle through: off -> mic -> system -> off
		if (audioMode === 'off') {
			await initAudioMic();
		} else if (audioMode === 'mic') {
			await stopAudio();
			await initAudioSystem();
		} else {
			await stopAudio();
		}
	};
	
	const getAudioLevel = (): number => {
		if (!audioAnalyzer || !audioDataArray || !audioEnabled) return 0;
		
		audioAnalyzer.getByteFrequencyData(audioDataArray as Uint8Array<ArrayBuffer>);
		
		// Calculate average level
		let sum = 0;
		for (let i = 0; i < audioDataArray.length; i++) {
			sum += audioDataArray[i];
		}
		return sum / audioDataArray.length / 255; // Normalize to 0-1
	};
	
	const getFrequencyBands = (): { bass: number; mid: number; high: number } => {
		if (!audioAnalyzer || !audioDataArray || !audioEnabled) {
			return { bass: 0, mid: 0, high: 0 };
		}
		
		audioAnalyzer.getByteFrequencyData(audioDataArray as Uint8Array<ArrayBuffer>);
		const len = audioDataArray.length;
		
		// Split into frequency bands
		let bass = 0, mid = 0, high = 0;
		const bassEnd = Math.floor(len * 0.1);
		const midEnd = Math.floor(len * 0.5);
		
		for (let i = 0; i < bassEnd; i++) bass += audioDataArray[i];
		for (let i = bassEnd; i < midEnd; i++) mid += audioDataArray[i];
		for (let i = midEnd; i < len; i++) high += audioDataArray[i];
		
		return {
			bass: bass / (bassEnd * 255),
			mid: mid / ((midEnd - bassEnd) * 255),
			high: high / ((len - midEnd) * 255)
		};
	};
	
	const updateEqualizer = () => {
		if (!audioAnalyzer || !audioDataArray || !audioEnabled) {
			eqBars = eqBars.map(v => v * 0.9); // Fade out
			return;
		}
		
		audioAnalyzer.getByteFrequencyData(audioDataArray as Uint8Array<ArrayBuffer>);
		const len = audioDataArray.length;
		const barCount = 16;
		const binSize = Math.floor(len / barCount);
		
		const newBars: number[] = [];
		for (let i = 0; i < barCount; i++) {
			let sum = 0;
			for (let j = 0; j < binSize; j++) {
				sum += audioDataArray[i * binSize + j];
			}
			const value = sum / binSize / 255;
			// Smooth transition
			newBars.push(Math.max(value, eqBars[i] * 0.85));
		}
		eqBars = newBars;
	};
	
	const handleWheel = (e: WheelEvent) => {
		e.preventDefault();
		// Scroll to fly forward/backward
		cameraTarget.z -= e.deltaY * 0.3;
	};
	
	const handleMouseMove = (e: MouseEvent) => {
		if (e.buttons === 1) {
			// Drag to strafe and change altitude
			cameraTarget.x += e.movementX * 0.5;
			cameraTarget.y -= e.movementY * 0.3;
			cameraTarget.y = Math.max(5, Math.min(100, cameraTarget.y));
		} else {
			// Hover detection when not dragging
			checkHover(e);
		}
	};
	
	const checkHover = (e: MouseEvent) => {
		if (!threeRef || !camera || !sceneCanvas) return;
		
		const THREE = threeRef;
		const rect = sceneCanvas.getBoundingClientRect();
		const mouse = new THREE.Vector2(
			((e.clientX - rect.left) / rect.width) * 2 - 1,
			-((e.clientY - rect.top) / rect.height) * 2 + 1
		);
		
		const raycaster = new THREE.Raycaster();
		raycaster.setFromCamera(mouse, camera);
		
		// First check for model orb hovers
		const modelMeshes: any[] = [];
		modelHub.forEach((orb: any) => {
			orb.traverse((child: any) => {
				if (child.isMesh) {
					child.userData.parentOrb = orb;
					modelMeshes.push(child);
				}
			});
		});
		
		const modelIntersects = raycaster.intersectObjects(modelMeshes, false);
		if (modelIntersects.length > 0) {
			const hit = modelIntersects[0].object;
			const orb = hit.userData.parentOrb;
			if (orb?.userData?.isModel) {
				hoveredModel = orb;
				sceneCanvas.style.cursor = 'var(--cyber-cursor-pointer)';
				// Show model info
				const stats = modelStats.get(orb.userData.modelId);
				const displayName = orb.userData.modelName || orb.userData.modelId;
				
				// Show floating tooltip near cursor
				modelTooltip = {
					visible: true,
					text: displayName,
					x: e.clientX,
					y: e.clientY - 40
				};
				
				if (stats && stats.chatCount > 0) {
					const lastUsedStr = stats.lastUsed ? stats.lastUsed.toLocaleDateString() : 'Never';
					currentGesture = `🤖 ${displayName} | ${stats.chatCount} chats | Last: ${lastUsedStr} | Click to chat`;
				} else {
					currentGesture = `🤖 ${displayName} | Click to chat`;
				}
				return;
			}
		} else if (hoveredModel) {
			hoveredModel = null;
			modelTooltip.visible = false;
			if (!currentGesture.startsWith('🎯')) currentGesture = '';
		}
		
		// Check for chat building hovers
		const chatBuildingArray = Array.from(chatBuildings.values());
		const allMeshes: any[] = [];
		
		for (const building of chatBuildingArray) {
			building.traverse((child: any) => {
				if (child.isMesh) {
					child.userData.parentBuilding = building;
					allMeshes.push(child);
				}
			});
		}
		
		const intersects = raycaster.intersectObjects(allMeshes, false);
		
		if (intersects.length > 0) {
			const hit = intersects[0].object;
			const building = hit.userData.parentBuilding;
			
			if (building?.userData?.isChat && building !== hoveredBuilding) {
				// Unhighlight previous
				if (hoveredBuilding) {
					setBuildingHighlight(hoveredBuilding, false);
				}
				// Highlight new
				hoveredBuilding = building;
				setBuildingHighlight(building, true);
				sceneCanvas.style.cursor = 'var(--cyber-cursor-pointer)';
			}
		} else if (hoveredBuilding) {
			setBuildingHighlight(hoveredBuilding, false);
			hoveredBuilding = null;
			sceneCanvas.style.cursor = 'var(--cyber-cursor-grab)';
		}
	};
	
	// Generate a unique ID for messages
	const generateMessageId = () => crypto.randomUUID();
	
	// Start a new chat with a specific model - creates persistent chat session
	const startNewChatWithModel = async (modelId: string, displayName?: string) => {
		const name = displayName || modelId;
		
		// Initialize cyberspace chat state
		cyberspaceChat = {
			active: true,
			modelId: modelId,
			displayName: name,
			chatId: '',
			messages: [],
			inputText: '',
			isLoading: true // Show loading while creating chat
		};
		currentGesture = `🤖 Creating chat with ${name}...`;
		
		try {
			// Create a new persistent chat in the database
			const chatData = {
				models: [modelId],
				messages: [],
				history: {
					messages: {},
					currentId: null
				},
				tags: [],
				timestamp: Date.now()
			};
			
			const newChat = await createNewChat(localStorage.token, chatData, null);
			
			if (newChat?.id) {
				cyberspaceChat.chatId = newChat.id;
				currentGesture = `🤖 Chatting with ${name}`;
				console.log(`Created new chat: ${newChat.id}`);
				
				// Refresh the chats store so sidebar updates
				const updatedChats = await getChatList(localStorage.token, 1);
				chats.set(updatedChats);
			} else {
				throw new Error('Failed to create chat');
			}
		} catch (error) {
			console.error('Failed to create chat:', error);
			currentGesture = `⚠️ Chat creation failed - using temporary session`;
			// Continue with temporary session if creation fails
		} finally {
			cyberspaceChat.isLoading = false;
		}
		
		// Focus input after render
		tick().then(() => {
			if (chatInputRef) chatInputRef.focus();
		});
	};
	
	// Save chat to database
	const saveChatToDatabase = async () => {
		if (!cyberspaceChat.chatId) return;
		
		try {
			// Build the chat history structure that Open WebUI expects
			const messagesMap: Record<string, any> = {};
			let lastId: string | null = null;
			
			cyberspaceChat.messages.forEach((msg, index) => {
				const msgId = msg.id || generateMessageId();
				messagesMap[msgId] = {
					id: msgId,
					parentId: lastId,
					childrenIds: [],
					role: msg.role,
					content: msg.content,
					timestamp: Math.floor(Date.now() / 1000)
				};
				
				// Link parent to child
				if (lastId && messagesMap[lastId]) {
					messagesMap[lastId].childrenIds.push(msgId);
				}
				
				lastId = msgId;
			});
			
			const chatData = {
				models: [cyberspaceChat.modelId],
				messages: cyberspaceChat.messages.map(m => ({
					role: m.role,
					content: m.content
				})),
				history: {
					messages: messagesMap,
					currentId: lastId
				},
				title: cyberspaceChat.messages[0]?.content?.slice(0, 50) || 'Cyberspace Chat',
				timestamp: Date.now()
			};
			
			await updateChatById(localStorage.token, cyberspaceChat.chatId, chatData);
		} catch (error) {
			console.error('Failed to save chat:', error);
		}
	};
	
	// Send message to model in cyberspace
	const sendCyberspaceMessage = async () => {
		if (!cyberspaceChat.inputText.trim() || cyberspaceChat.isLoading) return;
		
		const userMessage = cyberspaceChat.inputText.trim();
		const userMsgId = generateMessageId();
		cyberspaceChat.inputText = '';
		cyberspaceChat.messages = [...cyberspaceChat.messages, { role: 'user', content: userMessage, id: userMsgId }];
		cyberspaceChat.isLoading = true;
		
		try {
			// Build messages array for API
			const apiMessages = cyberspaceChat.messages.map(m => ({
				role: m.role,
				content: m.content
			}));
			
			// Call OpenAI-compatible chat endpoint
			const response = await fetch(`${WEBUI_API_BASE_URL}/chat/completions`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'Authorization': `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({
					model: cyberspaceChat.modelId,
					messages: apiMessages,
					stream: false
				})
			});
			
			if (!response.ok) {
				throw new Error(`API error: ${response.status}`);
			}
			
			const data = await response.json();
			const assistantMessage = data.choices?.[0]?.message?.content || 'No response';
			const assistantMsgId = generateMessageId();
			
			cyberspaceChat.messages = [...cyberspaceChat.messages, { role: 'assistant', content: assistantMessage, id: assistantMsgId }];
			
			// Save to database after each exchange
			await saveChatToDatabase();
		} catch (error) {
			console.error('Cyberspace chat error:', error);
			cyberspaceChat.messages = [...cyberspaceChat.messages, { 
				role: 'assistant', 
				content: `⚠️ Error: ${error instanceof Error ? error.message : 'Failed to get response'}` 
			}];
		} finally {
			cyberspaceChat.isLoading = false;
		}
	};
	
	// Open an existing chat in cyberspace chat interface
	const openExistingChat = async (chatIdToOpen: string, chatTitle: string, modelName: string) => {
		// Initialize cyberspace chat state
		cyberspaceChat = {
			active: true,
			modelId: modelName || '',
			displayName: chatTitle || 'Chat',
			chatId: chatIdToOpen,
			messages: [],
			inputText: '',
			isLoading: true
		};
		currentGesture = `📖 Loading chat history...`;
		
		try {
			// Fetch the full chat data
			const chatData = await getChatById(localStorage.token, chatIdToOpen);
			
			if (chatData?.chat) {
				// Extract messages from chat history
				const history = chatData.chat.history;
				const messages: { role: 'user' | 'assistant'; content: string; id?: string }[] = [];
				
				if (history?.messages && history?.currentId) {
					// Walk through the message tree from root to current
					const messageMap = history.messages;
					let currentMsgId = history.currentId;
					const messageChain: string[] = [];
					
					// Build chain from current back to root
					while (currentMsgId && messageMap[currentMsgId]) {
						messageChain.unshift(currentMsgId);
						currentMsgId = messageMap[currentMsgId].parentId;
					}
					
					// Extract messages in order
					for (const msgId of messageChain) {
						const msg = messageMap[msgId];
						if (msg && (msg.role === 'user' || msg.role === 'assistant')) {
							messages.push({
								role: msg.role,
								content: msg.content || '',
								id: msgId
							});
						}
					}
				}
				
				// Update model ID if available
				if (chatData.chat.models?.[0]) {
					cyberspaceChat.modelId = chatData.chat.models[0];
				}
				
				cyberspaceChat.messages = messages;
				cyberspaceChat.displayName = chatData.chat.title || chatTitle || 'Chat';
				currentGesture = `📖 ${cyberspaceChat.displayName}`;
				console.log(`Loaded chat with ${messages.length} messages`);
			}
		} catch (error) {
			console.error('Failed to load chat:', error);
			currentGesture = `⚠️ Failed to load chat`;
		} finally {
			cyberspaceChat.isLoading = false;
		}
		
		// Focus input after render
		tick().then(() => {
			if (chatInputRef) chatInputRef.focus();
		});
	};
	
	// Open chat in main OWUI interface
	const openInOWUI = () => {
		if (cyberspaceChat.chatId) {
			onClose(); // Close Pi Gateway
			goto(`/c/${cyberspaceChat.chatId}`); // Navigate to chat
		}
	};
	
	// Close cyberspace chat
	const closeCyberspaceChat = () => {
		cyberspaceChat.active = false;
		cyberspaceChat.modelId = '';
		cyberspaceChat.displayName = '';
		cyberspaceChat.chatId = '';
		cyberspaceChat.messages = [];
		cyberspaceChat.inputText = '';
		currentGesture = '';
	};
	
	const setBuildingHighlight = (building: any, highlight: boolean) => {
		building.traverse((child: any) => {
			if (child.isMesh && child.material) {
				if (highlight) {
					child.userData.originalOpacity = child.material.opacity;
					child.material.opacity = Math.min(1, child.material.opacity * 1.8);
					child.material.emissiveIntensity = 0.5;
				} else if (child.userData.originalOpacity !== undefined) {
					child.material.opacity = child.userData.originalOpacity;
					child.material.emissiveIntensity = 0;
				}
			}
		});
	};
	
	// Handle touch tap to select buildings on mobile
	const handleTouchSelect = (e: TouchEvent) => {
		if (!threeRef || !camera || !sceneCanvas) return;
		
		// Get touch position from changedTouches (available on touchend)
		const touch = e.changedTouches[0];
		if (!touch) return;
		
		const THREE = threeRef;
		const rect = sceneCanvas.getBoundingClientRect();
		const mouse = new THREE.Vector2(
			((touch.clientX - rect.left) / rect.width) * 2 - 1,
			-((touch.clientY - rect.top) / rect.height) * 2 + 1
		);
		
		const raycaster = new THREE.Raycaster();
		raycaster.setFromCamera(mouse, camera);
		
		// Check for intersections with chat buildings
		const chatBuildingArray = Array.from(chatBuildings.values());
		const allMeshes: any[] = [];
		
		for (const building of chatBuildingArray) {
			building.traverse((child: any) => {
				if (child.isMesh) {
					child.userData.parentBuilding = building;
					allMeshes.push(child);
				}
			});
		}
		
		const intersects = raycaster.intersectObjects(allMeshes, false);
		
		if (intersects.length > 0) {
			const hit = intersects[0].object;
			const building = hit.userData.parentBuilding;
			
			if (building?.userData?.isChat) {
				selectedChatBuilding = building;
				// On mobile, just select - don't auto-open chat (user can tap action button)
				currentGesture = `📍 ${building.userData.chatTitle}`;
			}
		} else {
			// Tapped empty space - deselect
			selectedChatBuilding = null;
			currentGesture = '';
		}
	};
	
	const handleClick = (e: MouseEvent) => {
		if (!threeRef || !camera || !sceneCanvas) return;
		
		const THREE = threeRef;
		const rect = sceneCanvas.getBoundingClientRect();
		const mouse = new THREE.Vector2(
			((e.clientX - rect.left) / rect.width) * 2 - 1,
			-((e.clientY - rect.top) / rect.height) * 2 + 1
		);
		
		const raycaster = new THREE.Raycaster();
		raycaster.setFromCamera(mouse, camera);
		
		// First check for model orb clicks
		const modelMeshes: any[] = [];
		modelHub.forEach((orb: any) => {
			orb.traverse((child: any) => {
				if (child.isMesh) {
					child.userData.parentOrb = orb;
					modelMeshes.push(child);
				}
			});
		});
		
		const modelIntersects = raycaster.intersectObjects(modelMeshes, false);
		if (modelIntersects.length > 0) {
			const hit = modelIntersects[0].object;
			const orb = hit.userData.parentOrb;
			if (orb?.userData?.isModel) {
				// Start new chat with this model
				startNewChatWithModel(orb.userData.modelId, orb.userData.modelName);
				return;
			}
		}
		
		// Check for intersections with chat buildings
		const chatBuildingArray = Array.from(chatBuildings.values());
		const allMeshes: any[] = [];
		
		for (const building of chatBuildingArray) {
			building.traverse((child: any) => {
				if (child.isMesh) {
					child.userData.parentBuilding = building;
					allMeshes.push(child);
				}
			});
		}
		
		const intersects = raycaster.intersectObjects(allMeshes, false);
		
		if (intersects.length > 0) {
			const hit = intersects[0].object;
			const building = hit.userData.parentBuilding;
			
			if (building?.userData?.isChat) {
				selectedChatBuilding = building;
				// Open the existing chat in cyberspace chat interface
				openExistingChat(building.userData.chatId, building.userData.chatTitle, building.userData.modelName);
			}
		} else {
			// Clicked empty space - deselect
			selectedChatBuilding = null;
		}
	};
	
	const handleKeyDown = (e: KeyboardEvent) => {
		// Don't intercept keys when cyberspace chat is active (allow typing)
		if (cyberspaceChat.active) {
			// Only handle Escape to close chat
			if (e.key === 'Escape') {
				closeCyberspaceChat();
				e.preventDefault();
			}
			return;
		}
		
		switch (e.key) {
			case 'ArrowUp':
			case 'w':
				cameraTarget.z -= 20; // Backward (toward now)
				e.preventDefault();
				break;
			case 'ArrowDown':
			case 's':
				cameraTarget.z += 20; // Forward (toward past)
				e.preventDefault();
				break;
			case 'ArrowLeft':
			case 'a':
				cameraTarget.x -= 15; // Strafe left (morning)
				e.preventDefault();
				break;
			case 'ArrowRight':
			case 'd':
				cameraTarget.x += 15; // Strafe right (evening)
				e.preventDefault();
				break;
			case 'q':
				cameraTarget.y = Math.min(120, cameraTarget.y + 10); // Ascend
				e.preventDefault();
				break;
			case 'e':
				cameraTarget.y = Math.max(5, cameraTarget.y - 10); // Descend
				e.preventDefault();
				break;
			case 'Enter':
				if (selectedChatBuilding?.userData?.chatId) {
					openSelectedChat();
				} else if (hoveredBuilding?.userData?.isChat) {
					selectedChatBuilding = hoveredBuilding;
				}
				e.preventDefault();
				break;
			case 'Escape':
				selectedChatBuilding = null;
				e.preventDefault();
				break;
			case ' ': // Spacebar - warp to next chat
				warpToNextChat();
				e.preventDefault();
				break;
		}
	};
	
	const warpToNextChat = () => {
		const chatBuildingArray = Array.from(chatBuildings.values());
		if (chatBuildingArray.length === 0) return;
		
		const aheadChats = chatBuildingArray
			.filter(b => b.position.z > cameraWorldPos.z + 5)
			.sort((a, b) => a.position.z - b.position.z);
		
		let target;
		if (aheadChats.length > 0) {
			target = aheadChats[0];
		} else {
			const sorted = [...chatBuildingArray].sort((a, b) => a.position.z - b.position.z);
			target = sorted[0];
		}
		
		// Start warp effect
		startWarp();
		
		selectedChatBuilding = target;
		cameraTarget.x = target.position.x;
		cameraTarget.z = target.position.z - 10;
		cameraTarget.y = Math.max(20, target.userData.height * 0.8);
		
		// Stop warp after arriving
		setTimeout(() => {
			stopWarp();
		}, 800);
	};
	
	onMount(async () => {
		checkMobile();
		await initThreeJS();
		
		window.addEventListener('resize', () => {
			checkMobile();
			if (camera && renderer) {
				camera.aspect = window.innerWidth / window.innerHeight;
				camera.updateProjectionMatrix();
				renderer.setSize(window.innerWidth, window.innerHeight);
			}
		});
		
		window.addEventListener('keydown', handleKeyDown);
	});
	
	onDestroy(() => {
		if (animationId) {
			cancelAnimationFrame(animationId);
		}
		
		if (gestureController) {
			gestureController.dispose();
		}
		
		// Clean up audio
		stopAudio();
		
		window.removeEventListener('keydown', handleKeyDown);
		
		if (renderer) {
			renderer.dispose();
		}
	});
</script>

<div 
	class="theater-container" 
	bind:this={container}
	on:mousemove={onChatDrag}
	on:mouseup={stopChatDrag}
	on:mouseleave={stopChatDrag}
	role="application"
>
	<canvas 
		bind:this={sceneCanvas}
		class="scene-canvas"
		on:wheel={(e) => { if (!isDraggingChat && !isResizingChat) handleWheel(e); }}
		on:mousemove={(e) => { if (!isDraggingChat && !isResizingChat) handleMouseMove(e); }}
		on:click={(e) => { if (!isDraggingChat && !isResizingChat) handleClick(e); }}
		on:touchend={(e) => { if (!joystickActive) handleTouchSelect(e); }}
	></canvas>
	
	<!-- Model name tooltip -->
	{#if modelTooltip.visible}
		<div 
			class="model-tooltip"
			style="left: {modelTooltip.x}px; top: {modelTooltip.y}px;"
		>
			{modelTooltip.text}
		</div>
	{/if}
	
	<div class="controls-overlay">
		<div class="top-bar">
			<div class="title">
				<span class="pi-icon">π</span>
				<span class="title-text">CYBERSPACE DATASTREAM</span>
			</div>
			
			<button class="close-btn" on:click={onClose} aria-label="Close Pi Gateway">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
					<path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
				</svg>
			</button>
		</div>
		
		<div class="info-panel">
			{#if selectedChatBuilding?.userData?.isChat}
				<!-- Selected Chat Info -->
				<div class="chat-info">
					<div class="chat-title">{selectedChatBuilding.userData.chatTitle}</div>
					<div class="chat-model">Model: {selectedChatBuilding.userData.modelName || 'Unknown'}</div>
					{#if selectedChatBuilding.userData.knowledgeBases?.length > 0}
						<div class="chat-kbs">
							<span class="kb-label">📚 Knowledge:</span>
							{#each selectedChatBuilding.userData.knowledgeBases as kb}
								<span class="kb-tag">{kb.name}</span>
							{/each}
						</div>
					{/if}
					<button class="open-chat-btn" on:click={openSelectedChat}>
						⚡ OPEN CHAT
					</button>
				</div>
			{:else}
				<!-- Default Stats - Timeline View -->
				<div class="info-text">
					<div class="stat">
						<span class="label">TIMELINE:</span>
						<span class="value zone-indicator">{getCurrentZone()}</span>
					</div>
					<div class="stat">
						<span class="label">CHATS:</span>
						<span class="value">{chatBuildings.size}{hasMoreChats ? '+' : ''}</span>
					</div>
					<div class="stat">
						<span class="label">ALTITUDE:</span>
						<span class="value">{cameraTarget.y.toFixed(0)}m</span>
					</div>
				</div>
				<div class="timeline-hint">
					{#if isLoadingMoreChats}
						<div class="loading-indicator">⟳ LOADING MORE CHATS...</div>
					{:else}
						<div>◀ NOW — scroll forward — PAST ▶</div>
					{/if}
				</div>
			{/if}
			
			{#if currentGesture}
				<div class="gesture-feedback">
					{currentGesture}
				</div>
			{/if}
		</div>
		
		<!-- Minimap -->
		<div class="minimap">
			<div class="minimap-title">TIMELINE</div>
			<div class="minimap-content">
				{#each Array.from(chatBuildings.values()) as building}
					<div 
						class="minimap-dot"
						class:selected={building === selectedChatBuilding}
						class:hovered={building === hoveredBuilding}
						style="left: {50 + (building.position.x / 50) * 40}%; top: {Math.min(90, Math.max(5, (building.position.z / (timelineEnd || 100)) * 85))}%;"
					></div>
				{/each}
				<div 
					class="minimap-camera"
					style="left: {50 + (cameraWorldPos.x / 50) * 40}%; top: {Math.min(90, Math.max(5, (cameraWorldPos.z / (timelineEnd || 100)) * 85))}%;"
				></div>
			</div>
			<div class="minimap-labels">
				<span>NOW</span>
				<span>PAST</span>
			</div>
		</div>
		
		<div class="bottom-controls">
			<button 
				class="control-btn" 
				class:active={gestureMode}
				on:click={toggleGestureMode}
			>
				{gestureMode ? '🤚 JACKED IN' : '👋 JACK IN'}
			</button>
			
			<button 
				class="control-btn audio-btn" 
				class:active={audioEnabled}
				on:click={cycleAudioMode}
			>
				{#if audioMode === 'off'}
					🔇 AUDIO
				{:else if audioMode === 'mic'}
					🎤 MIC
				{:else}
					🔊 SYSTEM
				{/if}
			</button>
			
			<!-- Equalizer visualization -->
			{#if audioEnabled}
				<div class="equalizer">
					{#each eqBars as bar, i}
						<div 
							class="eq-bar" 
							style="height: {Math.max(4, bar * 40)}px; background: {i < 4 ? '#ff00ff' : i < 10 ? '#00ffff' : '#00ff88'};"
						></div>
					{/each}
				</div>
			{/if}
			
			<button 
				class="control-btn new-chat-btn" 
				class:active={showModelSelector}
				on:click={() => showModelSelector = !showModelSelector}
			>
				➕ NEW CHAT
			</button>
			
			{#if !isMobile}
				<div class="help-text">
					{#if gestureMode}
						<div>✊ Fist → Past | ☝️ Point ← Now | ✋ Palm = Select</div>
						<div>✌️ Overview | 👎 Morning 👍 Evening | 🤟 Warp Next</div>
					{:else}
						<div>⌨️ WASD/Arrows = Move | Q/E = Up/Down | Space = Warp | Enter = Open | Esc = Deselect</div>
					{/if}
				</div>
			{/if}
		</div>
		
		<!-- Mobile Virtual Joystick -->
		{#if showMobileControls}
			<div class="mobile-joystick-container">
				<div 
					class="mobile-joystick"
					on:touchstart={handleJoystickStart}
					on:touchmove={handleJoystickMove}
					on:touchend={handleJoystickEnd}
					role="application"
					aria-label="Movement joystick - drag to move"
				>
					<div 
						class="joystick-knob"
						style="transform: translate({joystickDelta.x * 40}px, {joystickDelta.y * 40}px);"
					></div>
					<div class="joystick-directions">
						<span class="dir-label dir-up">▲</span>
						<span class="dir-label dir-down">▼</span>
						<span class="dir-label dir-left">◀</span>
						<span class="dir-label dir-right">▶</span>
					</div>
				</div>
			</div>
			
			<!-- Mobile Action Buttons -->
			<div class="mobile-action-buttons">
				<button 
					class="mobile-action-btn"
					on:click={() => { cameraTarget.y = Math.min(100, cameraTarget.y + 10); }}
					aria-label="Move up"
				>
					⬆️
				</button>
				<button 
					class="mobile-action-btn"
					on:click={() => { cameraTarget.y = Math.max(10, cameraTarget.y - 10); }}
					aria-label="Move down"
				>
					⬇️
				</button>
				<button 
					class="mobile-action-btn warp-btn"
					on:click={warpToNextChat}
					aria-label="Warp to next chat"
				>
					⚡
				</button>
				{#if selectedChatBuilding}
					<button 
						class="mobile-action-btn open-btn"
						on:click={openSelectedChat}
						aria-label="Open selected chat"
					>
						🚀
					</button>
				{/if}
			</div>
			
			<!-- Mobile Menu Toggle -->
			<button 
				class="mobile-menu-toggle"
				on:click={() => mobileMenuOpen = !mobileMenuOpen}
				aria-label="Toggle menu"
			>
				{mobileMenuOpen ? '✕' : '☰'}
			</button>
			
			<!-- Mobile Slide-out Menu -->
			{#if mobileMenuOpen}
				<div class="mobile-menu">
					<button 
						class="mobile-menu-item"
						on:click={() => { showModelSelector = !showModelSelector; mobileMenuOpen = false; }}
					>
						➕ New Chat
					</button>
					<button 
						class="mobile-menu-item"
						class:active={gestureMode}
						on:click={() => { toggleGestureMode(); mobileMenuOpen = false; }}
					>
						{gestureMode ? '🤚 Gesture Off' : '👋 Gesture On'}
					</button>
					<button 
						class="mobile-menu-item"
						class:active={audioEnabled}
						on:click={() => { cycleAudioMode(); }}
					>
						{audioMode === 'off' ? '🔇 Audio' : audioMode === 'mic' ? '🎤 Mic' : '🔊 System'}
					</button>
					<button 
						class="mobile-menu-item close-item"
						on:click={onClose}
					>
						✕ Close
					</button>
				</div>
			{/if}
		{/if}
		
		<!-- Model Selector Panel -->
		{#if showModelSelector}
			<div class="model-selector-panel">
				<div class="model-selector-header">
					<span>🤖 SELECT MODEL</span>
					<button class="model-selector-close" on:click={() => showModelSelector = false}>✕</button>
				</div>
				<div class="model-selector-list">
					{#each availableModelsList as model}
						<button 
							class="model-selector-item"
							on:click={() => { startNewChatWithModel(model.id, model.name); showModelSelector = false; }}
						>
							<span class="model-color-dot" style="background: {model.color};"></span>
							<span class="model-name">{model.name}</span>
							{#if model.chatCount > 0}
								<span class="model-chat-count">{model.chatCount}</span>
							{/if}
						</button>
					{/each}
					{#if availableModelsList.length === 0}
						<div class="model-selector-empty">No models available</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>
	
	<!-- Cyberspace Chat Interface -->
	{#if cyberspaceChat.active}
		<div 
			class="cyberspace-chat"
			style="width: {chatWindowSize.width}px; height: {chatWindowSize.height}px; {chatWindowPos.x !== 0 || chatWindowPos.y !== 0 ? `left: ${chatWindowPos.x}px; top: ${chatWindowPos.y}px; right: auto; transform: none;` : ''}"
		>
			<!-- Resize handles -->
			<div class="resize-handle resize-n" on:mousedown={(e) => startChatResize(e, 'n')} role="separator" aria-orientation="horizontal"></div>
			<div class="resize-handle resize-s" on:mousedown={(e) => startChatResize(e, 's')} role="separator" aria-orientation="horizontal"></div>
			<div class="resize-handle resize-e" on:mousedown={(e) => startChatResize(e, 'e')} role="separator" aria-orientation="vertical"></div>
			<div class="resize-handle resize-w" on:mousedown={(e) => startChatResize(e, 'w')} role="separator" aria-orientation="vertical"></div>
			<div class="resize-handle resize-ne" on:mousedown={(e) => startChatResize(e, 'ne')} role="separator"></div>
			<div class="resize-handle resize-nw" on:mousedown={(e) => startChatResize(e, 'nw')} role="separator"></div>
			<div class="resize-handle resize-se" on:mousedown={(e) => startChatResize(e, 'se')} role="separator"></div>
			<div class="resize-handle resize-sw" on:mousedown={(e) => startChatResize(e, 'sw')} role="separator"></div>
			
			<div 
				class="cyber-chat-header"
				on:mousedown={startChatDrag}
				role="button"
				tabindex="0"
				style="cursor: move;"
			>
				<div class="cyber-chat-title">
					<span class="cyber-model-icon">🤖</span>
					<span>{cyberspaceChat.displayName}</span>
					<span class="drag-hint">⋮⋮</span>
				</div>
				<button class="cyber-close-btn" on:click|stopPropagation={closeCyberspaceChat}>✕</button>
			</div>
			
			<div class="cyber-chat-messages">
				{#if cyberspaceChat.messages.length === 0 && !cyberspaceChat.isLoading}
					<div class="cyber-welcome">
						<div class="cyber-welcome-icon">💬</div>
						<div>Start chatting with {cyberspaceChat.displayName}</div>
						<div class="cyber-welcome-hint">Type a message below</div>
					</div>
				{/if}
				
				{#each cyberspaceChat.messages as message}
					<div class="cyber-message" class:user={message.role === 'user'} class:assistant={message.role === 'assistant'}>
						<div class="cyber-message-role">{message.role === 'user' ? '👤 You' : '🤖 AI'}</div>
						<div class="cyber-message-content">{message.content}</div>
					</div>
				{/each}
				
				{#if cyberspaceChat.isLoading}
					<div class="cyber-message assistant">
						<div class="cyber-message-role">🤖 AI</div>
						<div class="cyber-message-content cyber-loading">
							<span class="cyber-dot"></span>
							<span class="cyber-dot"></span>
							<span class="cyber-dot"></span>
						</div>
					</div>
				{/if}
			</div>
			
			<div class="cyber-chat-input">
				<input 
					type="text" 
					bind:this={chatInputRef}
					bind:value={cyberspaceChat.inputText}
					placeholder="Type your message..."
					on:keydown={(e) => e.key === 'Enter' && sendCyberspaceMessage()}
					disabled={cyberspaceChat.isLoading}
				/>
				<button 
					class="cyber-send-btn" 
					on:click={sendCyberspaceMessage}
					disabled={cyberspaceChat.isLoading || !cyberspaceChat.inputText.trim()}
				>
					⚡ SEND
				</button>
			</div>
			
			{#if cyberspaceChat.chatId}
				<div class="cyber-chat-footer">
					<button class="cyber-open-owui-btn" on:click={openInOWUI}>
						🚀 Open in Open WebUI
					</button>
				</div>
			{/if}
		</div>
	{/if}
	
	{#if gestureMode}
		<div class="gesture-container">
			<video bind:this={videoElement} class="gesture-video" autoplay playsinline muted>
				<track kind="captions" />
			</video>
			<canvas bind:this={gestureCanvas} class="gesture-canvas"></canvas>
			
			{#if videoDevices.length > 1}
				<div class="camera-selector">
					<button 
						class="camera-btn"
						on:click={() => showDeviceMenu = !showDeviceMenu}
						aria-label="Select Camera"
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="size-5">
							<path d="M12 9a3.75 3.75 0 1 0 0 7.5A3.75 3.75 0 0 0 12 9Z" />
							<path fill-rule="evenodd" d="M9.344 3.071a49.52 49.52 0 0 1 5.312 0c.967.052 1.83.585 2.332 1.39l.821 1.317c.24.383.645.643 1.11.71.386.054.77.113 1.152.177 1.432.239 2.429 1.493 2.429 2.909V18a3 3 0 0 1-3 3H4.5a3 3 0 0 1-3-3V9.574c0-1.416.997-2.67 2.429-2.909.382-.064.766-.123 1.151-.178a1.56 1.56 0 0 0 1.11-.71l.822-1.315a2.942 2.942 0 0 1 2.332-1.39ZM6.75 12.75a5.25 5.25 0 1 1 10.5 0 5.25 5.25 0 0 1-10.5 0Zm12-1.5a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z" clip-rule="evenodd" />
						</svg>
					</button>
					
					{#if showDeviceMenu}
						<div class="device-menu">
							{#each videoDevices as device}
								<button
									class="device-item"
									class:selected={device.deviceId === selectedDeviceId}
									on:click={() => switchCamera(device.deviceId)}
								>
									{device.label || `Camera ${videoDevices.indexOf(device) + 1}`}
								</button>
							{/each}
						</div>
					{/if}
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	/* Custom cyber cursor */
	.theater-container {
		position: relative;
		width: 100%;
		height: 100%;
		overflow: hidden;
		--cyber-cursor: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='3' fill='%2300ffff' opacity='0.8'/%3E%3Ccircle cx='16' cy='16' r='8' fill='none' stroke='%2300ffff' stroke-width='1' opacity='0.6'/%3E%3Cline x1='16' y1='0' x2='16' y2='10' stroke='%2300ffff' stroke-width='1' opacity='0.8'/%3E%3Cline x1='16' y1='22' x2='16' y2='32' stroke='%2300ffff' stroke-width='1' opacity='0.8'/%3E%3Cline x1='0' y1='16' x2='10' y2='16' stroke='%2300ffff' stroke-width='1' opacity='0.8'/%3E%3Cline x1='22' y1='16' x2='32' y2='16' stroke='%2300ffff' stroke-width='1' opacity='0.8'/%3E%3Ccircle cx='16' cy='16' r='14' fill='none' stroke='%23ff00ff' stroke-width='1' stroke-dasharray='4 4' opacity='0.4'/%3E%3C/svg%3E") 16 16, crosshair;
		--cyber-cursor-pointer: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32'%3E%3Cpolygon points='8,4 8,28 14,22 20,28 24,24 18,18 26,18' fill='%2300ffff' stroke='%23ff00ff' stroke-width='1'/%3E%3C/svg%3E") 8 4, pointer;
		--cyber-cursor-grab: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='4' fill='%2300ffff' opacity='0.9'/%3E%3Ccircle cx='16' cy='16' r='10' fill='none' stroke='%2300ffff' stroke-width='2' opacity='0.6'/%3E%3Cpath d='M16 2 L16 8 M16 24 L16 30 M2 16 L8 16 M24 16 L30 16' stroke='%23ff00ff' stroke-width='2' opacity='0.7'/%3E%3C/svg%3E") 16 16, grab;
		cursor: var(--cyber-cursor);
	}
	
	.scene-canvas {
		display: block;
		width: 100%;
		height: 100%;
		cursor: var(--cyber-cursor-grab);
	}
	
	.scene-canvas:active {
		cursor: var(--cyber-cursor-grab);
	}
	
	.controls-overlay {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		pointer-events: none;
	}
	
	.controls-overlay > * {
		pointer-events: auto;
	}
	
	.top-bar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1.5rem;
		background: linear-gradient(180deg, rgba(0, 0, 0, 0.8) 0%, transparent 100%);
	}
	
	.title {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		color: #00ffff;
		font-family: 'Courier New', monospace;
		text-shadow: 0 0 10px #00ffff, 0 0 20px #ff00ff;
		animation: title-pulse 2s ease-in-out infinite;
	}
	
	@keyframes title-pulse {
		0%, 100% { color: #00ffff; }
		50% { color: #ff00ff; }
	}
	
	.pi-icon {
		font-size: 2rem;
		font-family: 'Times New Roman', serif;
		font-weight: bold;
	}
	
	.title-text {
		font-size: 1.25rem;
		font-weight: bold;
		letter-spacing: 0.2em;
	}
	
	.close-btn {
		background: rgba(0, 255, 255, 0.1);
		border: 2px solid #00ffff;
		border-radius: 0.5rem;
		padding: 0.5rem;
		color: #00ffff;
		cursor: pointer;
		transition: all 0.2s;
		width: 2.5rem;
		height: 2.5rem;
	}
	
	.close-btn:hover {
		background: rgba(255, 0, 255, 0.2);
		box-shadow: 0 0 20px rgba(0, 255, 255, 0.5), 0 0 30px rgba(255, 0, 255, 0.3);
	}
	
	/* Model name tooltip */
	.model-tooltip {
		position: fixed;
		transform: translateX(-50%);
		background: rgba(0, 0, 20, 0.9);
		border: 1px solid #00ffff;
		border-radius: 0.5rem;
		padding: 0.5rem 1rem;
		color: #00ffff;
		font-family: 'Courier New', monospace;
		font-size: 0.9rem;
		font-weight: bold;
		text-shadow: 0 0 10px #00ffff;
		box-shadow: 0 0 20px rgba(0, 255, 255, 0.5), 0 0 40px rgba(255, 0, 255, 0.3);
		pointer-events: none;
		z-index: 2000;
		white-space: nowrap;
		animation: tooltip-fade-in 0.15s ease-out;
	}
	
	.model-tooltip::after {
		content: '';
		position: absolute;
		bottom: -6px;
		left: 50%;
		transform: translateX(-50%);
		border-left: 6px solid transparent;
		border-right: 6px solid transparent;
		border-top: 6px solid #00ffff;
	}
	
	@keyframes tooltip-fade-in {
		from { opacity: 0; transform: translateX(-50%) translateY(-5px); }
		to { opacity: 1; transform: translateX(-50%) translateY(0); }
	}
	
	.info-panel {
		position: absolute;
		top: 5rem;
		left: 1.5rem;
		background: rgba(0, 0, 0, 0.9);
		border: 2px solid #00ffff;
		border-radius: 0.5rem;
		padding: 1rem;
		font-family: 'Courier New', monospace;
		color: #00ffff;
		min-width: 200px;
		max-width: 300px;
		box-shadow: 0 0 20px rgba(0, 255, 255, 0.3), inset 0 0 20px rgba(255, 0, 255, 0.1);
	}
	
	.chat-info {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	
	.chat-title {
		font-size: 1.1rem;
		font-weight: bold;
		color: #ff00ff;
		text-shadow: 0 0 10px #ff00ff;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	
	.chat-model {
		font-size: 0.85rem;
		opacity: 0.8;
	}
	
	.chat-kbs {
		margin-top: 0.5rem;
		display: flex;
		flex-wrap: wrap;
		gap: 0.3rem;
		align-items: center;
	}
	
	.kb-label {
		font-size: 0.75rem;
		opacity: 0.8;
		margin-right: 0.2rem;
	}
	
	.kb-tag {
		background: rgba(255, 255, 0, 0.2);
		border: 1px solid #ffff00;
		border-radius: 0.25rem;
		padding: 0.15rem 0.4rem;
		font-size: 0.7rem;
		color: #ffff00;
		text-shadow: 0 0 5px #ffff00;
	}
	
	/* Model Selector Panel */
	.model-selector-panel {
		position: absolute;
		bottom: 5rem;
		left: 50%;
		transform: translateX(-50%);
		background: rgba(0, 0, 20, 0.95);
		border: 2px solid #00ffff;
		border-radius: 0.75rem;
		padding: 0;
		min-width: 280px;
		max-width: 400px;
		max-height: 50vh;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		box-shadow: 0 0 30px rgba(0, 255, 255, 0.4), 0 0 60px rgba(255, 0, 255, 0.2);
		animation: panel-slide-up 0.2s ease-out;
		z-index: 100;
	}
	
	@keyframes panel-slide-up {
		from { opacity: 0; transform: translateX(-50%) translateY(20px); }
		to { opacity: 1; transform: translateX(-50%) translateY(0); }
	}
	
	.model-selector-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem 1rem;
		border-bottom: 1px solid rgba(0, 255, 255, 0.3);
		color: #00ffff;
		font-family: 'Courier New', monospace;
		font-weight: bold;
		font-size: 0.9rem;
	}
	
	.model-selector-close {
		background: none;
		border: none;
		color: #ff00ff;
		font-size: 1.2rem;
		cursor: pointer;
		padding: 0.25rem;
		line-height: 1;
	}
	
	.model-selector-close:hover {
		color: #00ffff;
	}
	
	.model-selector-list {
		overflow-y: auto;
		max-height: 40vh;
		padding: 0.5rem;
	}
	
	.model-selector-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		width: 100%;
		padding: 0.6rem 0.75rem;
		background: rgba(0, 255, 255, 0.05);
		border: 1px solid transparent;
		border-radius: 0.5rem;
		color: #fff;
		font-family: 'Courier New', monospace;
		font-size: 0.85rem;
		cursor: pointer;
		transition: all 0.15s;
		text-align: left;
		margin-bottom: 0.25rem;
	}
	
	.model-selector-item:hover {
		background: rgba(0, 255, 255, 0.15);
		border-color: #00ffff;
		box-shadow: 0 0 10px rgba(0, 255, 255, 0.3);
	}
	
	.model-color-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		flex-shrink: 0;
		box-shadow: 0 0 8px currentColor;
	}
	
	.model-name {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	
	.model-chat-count {
		background: rgba(255, 0, 255, 0.3);
		color: #ff00ff;
		padding: 0.15rem 0.5rem;
		border-radius: 1rem;
		font-size: 0.75rem;
		font-weight: bold;
	}
	
	.model-selector-empty {
		text-align: center;
		color: rgba(0, 255, 255, 0.5);
		padding: 1rem;
		font-style: italic;
	}
	
	.new-chat-btn {
		background: linear-gradient(135deg, rgba(0, 255, 255, 0.2), rgba(255, 0, 255, 0.2)) !important;
		border-color: #00ffff !important;
	}
	
	.new-chat-btn:hover {
		box-shadow: 0 0 20px rgba(0, 255, 255, 0.5) !important;
	}
	
	.open-chat-btn {
		margin-top: 0.5rem;
		background: linear-gradient(135deg, rgba(255, 0, 255, 0.3), rgba(0, 255, 255, 0.3));
		border: 2px solid #ff00ff;
		border-radius: 0.5rem;
		padding: 0.75rem 1rem;
		color: #fff;
		font-family: 'Courier New', monospace;
		font-weight: bold;
		font-size: 1rem;
		cursor: pointer;
		transition: all 0.2s;
		text-shadow: 0 0 10px #ff00ff;
		box-shadow: 0 0 15px rgba(255, 0, 255, 0.4);
	}
	
	.open-chat-btn:hover {
		background: linear-gradient(135deg, rgba(255, 0, 255, 0.5), rgba(0, 255, 255, 0.5));
		box-shadow: 0 0 25px rgba(255, 0, 255, 0.6), 0 0 35px rgba(0, 255, 255, 0.4);
		transform: scale(1.02);
	}
	
	.info-text {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	
	.stat {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
	}
	
	.label {
		opacity: 0.7;
	}
	
	.value {
		font-weight: bold;
		color: #ff00ff;
		text-shadow: 0 0 5px #ff00ff, 0 0 10px #00ffff;
	}
	
	.zone-indicator {
		font-size: 0.9rem;
		letter-spacing: 0.1em;
	}
	
	.timeline-hint {
		margin-top: 0.75rem;
		padding-top: 0.75rem;
		border-top: 1px solid rgba(0, 255, 255, 0.2);
		font-size: 0.7rem;
		opacity: 0.7;
		text-align: center;
		color: #00ffff;
	}
	
	.loading-indicator {
		color: #ff00ff;
		animation: pulse-loading 1s ease-in-out infinite;
	}
	
	@keyframes pulse-loading {
		0%, 100% { opacity: 0.5; }
		50% { opacity: 1; }
	}
	
	.minimap {
		position: absolute;
		bottom: 8rem;
		left: 1.5rem;
		width: 120px;
		height: 180px;
		background: rgba(0, 0, 0, 0.85);
		border: 2px solid #00ffff;
		border-radius: 0.5rem;
		padding: 0.5rem;
		font-family: 'Courier New', monospace;
		box-shadow: 0 0 15px rgba(0, 255, 255, 0.3);
	}
	
	.minimap-title {
		font-size: 0.6rem;
		color: #00ffff;
		text-align: center;
		margin-bottom: 0.3rem;
		letter-spacing: 0.1em;
		opacity: 0.8;
	}
	
	.minimap-content {
		position: relative;
		width: 100%;
		height: calc(100% - 30px);
		background: rgba(0, 50, 50, 0.3);
		border-radius: 0.25rem;
		overflow: hidden;
	}
	
	.minimap-dot {
		position: absolute;
		width: 4px;
		height: 4px;
		background: #00aaaa;
		border-radius: 50%;
		transform: translate(-50%, -50%);
		transition: all 0.1s;
	}
	
	.minimap-dot.selected {
		width: 8px;
		height: 8px;
		background: #ff00ff;
		box-shadow: 0 0 8px #ff00ff;
	}
	
	.minimap-dot.hovered {
		width: 6px;
		height: 6px;
		background: #ffff00;
		box-shadow: 0 0 6px #ffff00;
	}
	
	.minimap-camera {
		position: absolute;
		width: 0;
		height: 0;
		border-left: 6px solid transparent;
		border-right: 6px solid transparent;
		border-bottom: 10px solid #00ff00;
		transform: translate(-50%, -50%);
		filter: drop-shadow(0 0 4px #00ff00);
	}
	
	.minimap-labels {
		display: flex;
		justify-content: space-between;
		font-size: 0.5rem;
		color: #00ffff;
		opacity: 0.6;
		margin-top: 0.2rem;
	}
	
	.gesture-feedback {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid rgba(0, 255, 255, 0.3);
		text-align: center;
		color: #ff00ff;
		animation: pulse 1s ease-in-out infinite;
	}
	
	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.7; }
	}
	
	.bottom-controls {
		position: absolute;
		bottom: 0;
		left: 0;
		right: 0;
		padding: 2rem;
		background: linear-gradient(0deg, rgba(0, 0, 0, 0.8) 0%, transparent 100%);
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
	}
	
	.control-btn {
		background: rgba(0, 255, 255, 0.1);
		border: 2px solid #00ffff;
		border-radius: 0.5rem;
		padding: 0.75rem 2rem;
		color: #00ffff;
		font-family: 'Courier New', monospace;
		font-weight: bold;
		cursor: pointer;
		transition: all 0.2s;
		font-size: 1rem;
		box-shadow: 0 0 10px rgba(0, 255, 255, 0.2), inset 0 0 10px rgba(255, 0, 255, 0.1);
	}
	
	.control-btn:hover {
		background: rgba(255, 0, 255, 0.2);
		box-shadow: 0 0 20px rgba(0, 255, 255, 0.5), 0 0 30px rgba(255, 0, 255, 0.3);
		transform: scale(1.05);
		color: #ff00ff;
	}
	
	.control-btn.active {
		background: rgba(255, 0, 255, 0.3);
		border-color: #ff00ff;
		color: #ff00ff;
		animation: pulse-border 2s ease-in-out infinite;
	}
	
	@keyframes pulse-border {
		0%, 100% {
			box-shadow: 0 0 10px rgba(0, 255, 255, 0.5), 0 0 20px rgba(255, 0, 255, 0.3);
		}
		50% {
			box-shadow: 0 0 30px rgba(0, 255, 255, 0.8), 0 0 40px rgba(255, 0, 255, 0.6);
		}
	}
	
	/* Equalizer visualization */
	.equalizer {
		display: flex;
		align-items: flex-end;
		gap: 2px;
		height: 40px;
		padding: 4px 8px;
		background: rgba(0, 0, 20, 0.8);
		border: 1px solid #00ffff;
		border-radius: 4px;
		box-shadow: 0 0 10px rgba(0, 255, 255, 0.3), inset 0 0 5px rgba(255, 0, 255, 0.1);
	}
	
	.eq-bar {
		width: 4px;
		min-height: 4px;
		border-radius: 2px;
		transition: height 0.05s ease-out;
		box-shadow: 0 0 5px currentColor;
	}
	
	.help-text {
		font-family: 'Courier New', monospace;
		color: #00ffff;
		opacity: 0.7;
		font-size: 0.875rem;
		text-align: center;
	}
	
	.gesture-container {
		position: absolute;
		bottom: 1rem;
		right: 1rem;
		width: 320px;
		height: 240px;
		border: 2px solid #00ffff;
		border-radius: 0.5rem;
		overflow: hidden;
		background: black;
		box-shadow: 0 0 20px rgba(0, 255, 255, 0.5), 0 0 30px rgba(255, 0, 255, 0.3), inset 0 0 20px rgba(0, 255, 255, 0.1);
	}
	
	.gesture-video {
		position: absolute;
		width: 100%;
		height: 100%;
		object-fit: cover;
		opacity: 0.6;
	}
	
	.gesture-canvas {
		position: absolute;
		width: 100%;
		height: 100%;
	}
	
	.camera-selector {
		position: absolute;
		top: 0.5rem;
		right: 0.5rem;
		z-index: 10;
	}
	
	.camera-btn {
		background: rgba(0, 0, 0, 0.7);
		border: 1px solid #00ffff;
		border-radius: 0.375rem;
		padding: 0.5rem;
		color: #00ffff;
		cursor: pointer;
		transition: all 0.2s;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	
	.camera-btn:hover {
		background: rgba(255, 0, 255, 0.2);
		box-shadow: 0 0 10px rgba(0, 255, 255, 0.5), 0 0 15px rgba(255, 0, 255, 0.3);
		color: #ff00ff;
	}
	
	.device-menu {
		position: absolute;
		top: 100%;
		right: 0;
		margin-top: 0.5rem;
		background: rgba(0, 0, 0, 0.95);
		border: 2px solid #00ffff;
		border-radius: 0.5rem;
		overflow-y: auto;
		overflow-x: hidden;
		min-width: 200px;
		max-height: 200px;
		box-shadow: 0 0 20px rgba(0, 255, 255, 0.5), 0 0 30px rgba(255, 0, 255, 0.3);
	}
	
	.device-menu::-webkit-scrollbar {
		width: 6px;
	}
	
	.device-menu::-webkit-scrollbar-track {
		background: rgba(0, 255, 255, 0.1);
	}
	
	.device-menu::-webkit-scrollbar-thumb {
		background: rgba(0, 255, 255, 0.5);
		border-radius: 3px;
	}
	
	.device-menu::-webkit-scrollbar-thumb:hover {
		background: rgba(255, 0, 255, 0.7);
	}
	
	.device-item {
		display: block;
		width: 100%;
		padding: 0.75rem 1rem;
		background: transparent;
		border: none;
		color: #00ffff;
		font-family: 'Courier New', monospace;
		font-size: 0.875rem;
		text-align: left;
		cursor: pointer;
		transition: all 0.2s;
		border-bottom: 1px solid rgba(0, 255, 255, 0.2);
	}
	
	.device-item:last-child {
		border-bottom: none;
	}
	
	.device-item:hover {
		background: rgba(255, 0, 255, 0.2);
		color: #ff00ff;
	}
	
	.device-item.selected {
		background: rgba(255, 0, 255, 0.3);
		color: #ff00ff;
		font-weight: bold;
		box-shadow: inset 0 0 10px rgba(0, 255, 255, 0.2);
	}
	
	/* Cyberspace Chat Interface */
	.cyberspace-chat {
		position: fixed;
		right: 1.5rem;
		top: 50%;
		transform: translateY(-50%);
		width: 400px;
		max-height: 70vh;
		background: rgba(0, 0, 20, 0.6);
		border: 2px solid #00ffff;
		border-radius: 1rem;
		display: flex;
		flex-direction: column;
		box-shadow: 0 0 30px rgba(0, 255, 255, 0.4), 0 0 60px rgba(255, 0, 255, 0.2);
		font-family: 'Courier New', monospace;
		z-index: 1000;
		animation: cyber-slide-in 0.3s ease-out;
		backdrop-filter: blur(4px);
	}
	
	@keyframes cyber-slide-in {
		from { opacity: 0; transform: translateY(-50%) translateX(50px); }
		to { opacity: 1; transform: translateY(-50%) translateX(0); }
	}
	
	.cyber-chat-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		border-bottom: 1px solid rgba(0, 255, 255, 0.3);
		background: linear-gradient(135deg, rgba(0, 255, 255, 0.1), rgba(255, 0, 255, 0.1));
		cursor: move;
		user-select: none;
	}
	
	.cyber-chat-header:active {
		background: linear-gradient(135deg, rgba(0, 255, 255, 0.2), rgba(255, 0, 255, 0.2));
	}
	
	.cyber-chat-title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: #00ffff;
		font-weight: bold;
		text-shadow: 0 0 10px #00ffff;
	}
	
	.drag-hint {
		opacity: 0.4;
		font-size: 0.8rem;
		margin-left: 0.5rem;
		letter-spacing: 2px;
	}
	
	.cyber-model-icon {
		font-size: 1.5rem;
	}
	
	.cyber-close-btn {
		background: transparent;
		border: 1px solid #ff00ff;
		color: #ff00ff;
		width: 2rem;
		height: 2rem;
		border-radius: 50%;
		cursor: pointer;
		font-size: 1rem;
		transition: all 0.2s;
	}
	
	.cyber-close-btn:hover {
		background: rgba(255, 0, 255, 0.3);
		box-shadow: 0 0 15px #ff00ff;
	}
	
	.cyber-chat-messages {
		flex: 1;
		overflow-y: auto;
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
		min-height: 100px;
	}
	
	/* Resize handles */
	.resize-handle {
		position: absolute;
		background: transparent;
		z-index: 10;
	}
	
	.resize-n, .resize-s {
		left: 10px;
		right: 10px;
		height: 8px;
		cursor: ns-resize;
	}
	.resize-n { top: -4px; }
	.resize-s { bottom: -4px; }
	
	.resize-e, .resize-w {
		top: 10px;
		bottom: 10px;
		width: 8px;
		cursor: ew-resize;
	}
	.resize-e { right: -4px; }
	.resize-w { left: -4px; }
	
	.resize-ne, .resize-nw, .resize-se, .resize-sw {
		width: 16px;
		height: 16px;
	}
	.resize-ne { top: -4px; right: -4px; cursor: nesw-resize; }
	.resize-nw { top: -4px; left: -4px; cursor: nwse-resize; }
	.resize-se { bottom: -4px; right: -4px; cursor: nwse-resize; }
	.resize-sw { bottom: -4px; left: -4px; cursor: nesw-resize; }
	
	/* Visual indicator on corner handles */
	.resize-se::after {
		content: '';
		position: absolute;
		bottom: 4px;
		right: 4px;
		width: 10px;
		height: 10px;
		border-right: 2px solid rgba(0, 255, 255, 0.5);
		border-bottom: 2px solid rgba(0, 255, 255, 0.5);
	}
	
	.cyber-welcome {
		text-align: center;
		color: #00ffff;
		opacity: 0.7;
		padding: 2rem;
	}
	
	.cyber-welcome-icon {
		font-size: 3rem;
		margin-bottom: 1rem;
	}
	
	.cyber-welcome-hint {
		font-size: 0.8rem;
		margin-top: 0.5rem;
		opacity: 0.6;
	}
	
	.cyber-message {
		padding: 0.75rem;
		border-radius: 0.5rem;
		max-width: 90%;
	}
	
	.cyber-message.user {
		background: rgba(255, 0, 255, 0.2);
		border: 1px solid rgba(255, 0, 255, 0.5);
		margin-left: auto;
	}
	
	.cyber-message.assistant {
		background: rgba(0, 255, 255, 0.1);
		border: 1px solid rgba(0, 255, 255, 0.3);
		margin-right: auto;
	}
	
	.cyber-message-role {
		font-size: 0.7rem;
		opacity: 0.7;
		margin-bottom: 0.3rem;
	}
	
	.cyber-message-content {
		color: #fff;
		font-size: 0.9rem;
		line-height: 1.4;
		white-space: pre-wrap;
		word-break: break-word;
	}
	
	.cyber-loading {
		display: flex;
		gap: 0.3rem;
	}
	
	.cyber-dot {
		width: 8px;
		height: 8px;
		background: #00ffff;
		border-radius: 50%;
		animation: cyber-pulse 1s infinite;
	}
	
	.cyber-dot:nth-child(2) { animation-delay: 0.2s; }
	.cyber-dot:nth-child(3) { animation-delay: 0.4s; }
	
	@keyframes cyber-pulse {
		0%, 100% { opacity: 0.3; transform: scale(0.8); }
		50% { opacity: 1; transform: scale(1.2); }
	}
	
	.cyber-chat-input {
		display: flex;
		gap: 0.5rem;
		padding: 1rem;
		border-top: 1px solid rgba(0, 255, 255, 0.3);
	}
	
	.cyber-chat-input input {
		flex: 1;
		background: rgba(0, 0, 0, 0.5);
		border: 1px solid #00ffff;
		border-radius: 0.5rem;
		padding: 0.75rem;
		color: #fff;
		font-family: 'Courier New', monospace;
		font-size: 0.9rem;
	}
	
	.cyber-chat-input input:focus {
		outline: none;
		box-shadow: 0 0 15px rgba(0, 255, 255, 0.5);
	}
	
	.cyber-chat-input input::placeholder {
		color: rgba(0, 255, 255, 0.5);
	}
	
	.cyber-send-btn {
		background: linear-gradient(135deg, rgba(255, 0, 255, 0.3), rgba(0, 255, 255, 0.3));
		border: 2px solid #ff00ff;
		border-radius: 0.5rem;
		padding: 0.75rem 1rem;
		color: #ff00ff;
		font-family: 'Courier New', monospace;
		font-weight: bold;
		cursor: pointer;
		transition: all 0.2s;
		text-shadow: 0 0 5px #ff00ff;
	}
	
	.cyber-send-btn:hover:not(:disabled) {
		background: rgba(255, 0, 255, 0.4);
		box-shadow: 0 0 20px #ff00ff;
	}
	
	.cyber-send-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	
	.cyber-chat-footer {
		padding: 0.75rem 1rem;
		border-top: 1px solid rgba(0, 255, 255, 0.2);
		display: flex;
		justify-content: center;
	}
	
	.cyber-open-owui-btn {
		background: linear-gradient(135deg, rgba(0, 255, 255, 0.2), rgba(255, 0, 255, 0.2));
		border: 1px solid #00ffff;
		border-radius: 0.5rem;
		padding: 0.5rem 1rem;
		color: #00ffff;
		font-family: 'Courier New', monospace;
		font-size: 0.85rem;
		cursor: pointer;
		transition: all 0.2s;
		text-shadow: 0 0 5px #00ffff;
	}
	
	.cyber-open-owui-btn:hover {
		background: rgba(0, 255, 255, 0.3);
		box-shadow: 0 0 15px rgba(0, 255, 255, 0.5);
	}
	
	/* ========== MOBILE STYLES ========== */
	
	/* Mobile Virtual Joystick */
	.mobile-joystick-container {
		position: absolute;
		bottom: 2rem;
		left: 1.5rem;
		z-index: 100;
	}
	
	.mobile-joystick {
		width: 120px;
		height: 120px;
		background: rgba(0, 0, 20, 0.8);
		border: 2px solid #00ffff;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		position: relative;
		box-shadow: 0 0 20px rgba(0, 255, 255, 0.4), inset 0 0 30px rgba(0, 255, 255, 0.1);
		touch-action: none;
	}
	
	.joystick-knob {
		width: 50px;
		height: 50px;
		background: linear-gradient(135deg, #00ffff, #ff00ff);
		border-radius: 50%;
		box-shadow: 0 0 15px #00ffff, 0 0 25px #ff00ff;
		transition: transform 0.05s ease-out;
	}
	
	.joystick-directions {
		position: absolute;
		width: 100%;
		height: 100%;
		pointer-events: none;
	}
	
	.dir-label {
		position: absolute;
		color: rgba(0, 255, 255, 0.5);
		font-size: 0.8rem;
	}
	
	.dir-up { top: 8px; left: 50%; transform: translateX(-50%); }
	.dir-down { bottom: 8px; left: 50%; transform: translateX(-50%); }
	.dir-left { left: 8px; top: 50%; transform: translateY(-50%); }
	.dir-right { right: 8px; top: 50%; transform: translateY(-50%); }
	
	/* Mobile Action Buttons */
	.mobile-action-buttons {
		position: absolute;
		bottom: 2rem;
		right: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		z-index: 100;
	}
	
	.mobile-action-btn {
		width: 56px;
		height: 56px;
		border-radius: 50%;
		background: rgba(0, 0, 20, 0.8);
		border: 2px solid #00ffff;
		color: #00ffff;
		font-size: 1.5rem;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		box-shadow: 0 0 15px rgba(0, 255, 255, 0.3);
		transition: all 0.2s;
		-webkit-tap-highlight-color: transparent;
	}
	
	.mobile-action-btn:active {
		transform: scale(0.95);
		background: rgba(0, 255, 255, 0.2);
	}
	
	.mobile-action-btn.warp-btn {
		border-color: #ff00ff;
		box-shadow: 0 0 15px rgba(255, 0, 255, 0.3);
	}
	
	.mobile-action-btn.open-btn {
		border-color: #00ff88;
		box-shadow: 0 0 15px rgba(0, 255, 136, 0.3);
	}
	
	/* Mobile Menu Toggle */
	.mobile-menu-toggle {
		position: absolute;
		top: 1rem;
		right: 1rem;
		width: 48px;
		height: 48px;
		border-radius: 0.5rem;
		background: rgba(0, 0, 20, 0.8);
		border: 2px solid #00ffff;
		color: #00ffff;
		font-size: 1.5rem;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		z-index: 200;
		box-shadow: 0 0 15px rgba(0, 255, 255, 0.3);
		-webkit-tap-highlight-color: transparent;
	}
	
	/* Mobile Slide-out Menu */
	.mobile-menu {
		position: absolute;
		top: 4.5rem;
		right: 1rem;
		background: rgba(0, 0, 20, 0.95);
		border: 2px solid #00ffff;
		border-radius: 0.75rem;
		padding: 0.5rem;
		z-index: 150;
		min-width: 180px;
		box-shadow: 0 0 30px rgba(0, 255, 255, 0.4);
		animation: menu-slide-in 0.2s ease-out;
	}
	
	@keyframes menu-slide-in {
		from { opacity: 0; transform: translateY(-10px); }
		to { opacity: 1; transform: translateY(0); }
	}
	
	.mobile-menu-item {
		display: block;
		width: 100%;
		padding: 0.875rem 1rem;
		background: transparent;
		border: none;
		border-radius: 0.5rem;
		color: #00ffff;
		font-family: 'Courier New', monospace;
		font-size: 1rem;
		text-align: left;
		cursor: pointer;
		transition: all 0.15s;
		-webkit-tap-highlight-color: transparent;
	}
	
	.mobile-menu-item:active,
	.mobile-menu-item.active {
		background: rgba(0, 255, 255, 0.2);
	}
	
	.mobile-menu-item.close-item {
		color: #ff00ff;
		border-top: 1px solid rgba(0, 255, 255, 0.2);
		margin-top: 0.5rem;
		padding-top: 1rem;
	}
	
	/* Mobile Responsive Adjustments */
	@media (max-width: 768px) {
		.top-bar {
			padding: 0.75rem 1rem;
		}
		
		.title-text {
			font-size: 0.9rem;
			letter-spacing: 0.1em;
		}
		
		.pi-icon {
			font-size: 1.5rem;
		}
		
		.close-btn {
			display: none; /* Use mobile menu instead */
		}
		
		.info-panel {
			top: auto;
			bottom: 10rem;
			left: 50%;
			transform: translateX(-50%);
			max-width: calc(100vw - 3rem);
			font-size: 0.8rem;
			padding: 0.75rem;
		}
		
		.minimap {
			display: none; /* Hide minimap on mobile - too small to be useful */
		}
		
		.bottom-controls {
			display: none; /* Use mobile controls instead */
		}
		
		.gesture-container {
			width: 200px;
			height: 150px;
			bottom: auto;
			top: 4.5rem;
			right: 1rem;
		}
		
		/* Cyberspace Chat - Full screen on mobile */
		.cyberspace-chat {
			position: fixed !important;
			left: 0 !important;
			right: 0 !important;
			top: 0 !important;
			bottom: 0 !important;
			width: 100% !important;
			height: 100% !important;
			max-height: 100vh !important;
			border-radius: 0;
			transform: none !important;
			z-index: 1000;
		}
		
		.resize-handle {
			display: none; /* No resize on mobile */
		}
		
		.cyber-chat-header {
			cursor: default;
			padding: 0.75rem 1rem;
		}
		
		.drag-hint {
			display: none;
		}
		
		.cyber-chat-messages {
			padding: 0.75rem;
		}
		
		.cyber-chat-input {
			padding: 0.75rem;
		}
		
		.cyber-chat-input input {
			font-size: 16px; /* Prevent iOS zoom */
		}
		
		/* Model Selector - Full width on mobile */
		.model-selector-panel {
			left: 1rem;
			right: 1rem;
			bottom: 10rem;
			transform: none;
			max-width: none;
			max-height: 40vh;
		}
		
		.model-selector-item {
			padding: 0.875rem 1rem;
			min-height: 48px; /* Touch-friendly */
		}
		
		/* Chat info panel adjustments */
		.chat-info {
			font-size: 0.85rem;
		}
		
		.chat-title {
			font-size: 1rem;
		}
		
		.open-chat-btn {
			padding: 0.875rem 1rem;
			font-size: 0.9rem;
			min-height: 48px;
		}
		
		/* Model tooltip - hide on mobile (use tap instead) */
		.model-tooltip {
			display: none;
		}
	}
	
	/* Extra small screens */
	@media (max-width: 400px) {
		.mobile-joystick {
			width: 100px;
			height: 100px;
		}
		
		.joystick-knob {
			width: 40px;
			height: 40px;
		}
		
		.mobile-action-btn {
			width: 48px;
			height: 48px;
			font-size: 1.25rem;
		}
		
		.info-panel {
			font-size: 0.75rem;
			padding: 0.5rem;
		}
	}
</style>
