<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { chats, chatId } from '$lib/stores';
	import { getChatList } from '$lib/apis/chats';
	import { goto } from '$app/navigation';
	import { MediaPipeGestureController, type GestureType, type DualGestureType, type AllGestureTypes } from '$lib/utils/mediapipe-gesture';
	
	export let onClose: () => void;
	
	// Chat data for visualization
	let userChats: any[] = [];
	let chatBuildings: Map<string, any> = new Map(); // chatId -> building mesh
	let hoveredChat: any = null;
	let selectedChatBuilding: any = null;
	
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
	
	const initThreeJS = async () => {
		// @ts-ignore - CDN import
		const THREE = await import('https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js');
		
		scene = new THREE.Scene();
		scene.background = new THREE.Color(0x000000);
		scene.fog = new THREE.Fog(0x000000, 50, 200);
		
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
		renderer.setPixelRatio(window.devicePixelRatio);
		
		createChatGraph(THREE);
		
		animate(THREE);
	};
	
	let dataStreams: any[] = [];
	let buildings: any[] = [];
	let flySpeed = 0;
	let targetBuilding: any = null;
	let cameraTarget = { x: 0, y: 25, z: 0 };
	let cameraWorldPos = { x: 0, z: 0 };
	let electricArcs: any[] = [];
	
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
		
		// Initial chunk loading (procedural buildings in outer areas)
		updateChunks();
	};
	
	// Linear timeline settings
	const TIMELINE_SPACING = 15; // Distance between chats on Z-axis
	const LANE_WIDTH = 12; // Width of each model lane on X-axis
	let timelineStart = 0; // Z position of oldest chat
	let timelineEnd = 0; // Z position of newest chat
	
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
			// Load recent chats
			const chatList = await getChatList(localStorage.token, 1, true, true);
			userChats = chatList || [];
			
			if (userChats.length === 0) return;
			
			// Sort chats by creation/update time (newest/latest first at start)
			const sortedChats = [...userChats].sort((a, b) => {
				const timeA = a.created_at || a.updated_at || 0;
				const timeB = b.created_at || b.updated_at || 0;
				return timeB - timeA; // Newest/latest first
			});
			
			const chatCount = Math.min(sortedChats.length, 50);
			
			// Create timeline markers and buildings
			timelineStart = 0;
			timelineEnd = chatCount * TIMELINE_SPACING;
			
			createTimelineMarkers(THREE, sortedChats.slice(0, chatCount));
			
			// Create buildings along timeline - X position based on time of day
			for (let i = 0; i < chatCount; i++) {
				const chat = sortedChats[i];
				const timestamp = chat.created_at || chat.updated_at || 0;
				
				// X position based on time of day: morning (left) to evening (right)
				// -12 to +12 hours from midday, scaled to -40 to +40 units
				const timeOffset = getTimeOfDayOffset(timestamp);
				const x = timeOffset * 3.5; // Scale factor for spread
				
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
			
		} catch (error) {
			console.error('Failed to load chats:', error);
		}
	};
	
	const createTimelineMarkers = (THREE: any, sortedChats: any[]) => {
		const railLength = sortedChats.length * TIMELINE_SPACING + 50;
		
		// === TIME OF DAY GRID (X-axis) ===
		// Hours from 0 (midnight) to 24 (midnight), with 12pm at center (X=0)
		// X position = (hour - 12) * 3.5
		const timeGridColor = 0x006688;
		const noonColor = 0x00ffff;
		
		for (let hour = 0; hour <= 24; hour += 3) { // Every 3 hours for cleaner grid
			const xPos = (hour - 12) * 3.5;
			const isNoon = hour === 12;
			const isMidnight = hour === 0 || hour === 24;
			const is6am = hour === 6;
			const is6pm = hour === 18;
			
			// Vertical line along Z-axis for this hour
			const lineGeometry = new THREE.BufferGeometry().setFromPoints([
				new THREE.Vector3(xPos, 0.05, -30),
				new THREE.Vector3(xPos, 0.05, railLength)
			]);
			const lineColor = isNoon ? noonColor : (isMidnight ? 0xff00ff : (is6am || is6pm ? 0xffaa00 : timeGridColor));
			const lineOpacity = isNoon ? 0.7 : (isMidnight || is6am || is6pm ? 0.5 : 0.3);
			const lineMaterial = new THREE.LineBasicMaterial({ color: lineColor, transparent: true, opacity: lineOpacity });
			scene.add(new THREE.Line(lineGeometry, lineMaterial));
			
			// Vertical post at start of timeline for this hour
			const postGeometry = new THREE.BufferGeometry().setFromPoints([
				new THREE.Vector3(xPos, 0, -30),
				new THREE.Vector3(xPos, 15, -30)
			]);
			const postMaterial = new THREE.LineBasicMaterial({ color: lineColor, transparent: true, opacity: 0.8 });
			scene.add(new THREE.Line(postGeometry, postMaterial));
			
			// Hour label - larger and higher
			const hourLabel = hour === 0 ? '12AM' : hour === 12 ? '12PM' : hour === 24 ? '12AM' : 
				hour < 12 ? `${hour}AM` : `${hour - 12}PM`;
			const labelColor = isNoon ? noonColor : (isMidnight ? 0xff00ff : (is6am || is6pm ? 0xffaa00 : 0x00cccc));
			const hourSprite = createTextSprite(THREE, hourLabel, labelColor);
			hourSprite.position.set(xPos, 18, -30);
			hourSprite.scale.set(8, 2, 1);
			scene.add(hourSprite);
		}
		
		// Add "MORNING" and "EVENING" labels - positioned along the sides
		const morningSprite = createTextSprite(THREE, '🌅 MORNING', 0xffaa00);
		morningSprite.position.set(-35, 50, railLength / 2);
		morningSprite.scale.set(12, 3, 1);
		scene.add(morningSprite);
		
		const eveningSprite = createTextSprite(THREE, 'EVENING 🌙', 0x8800ff);
		eveningSprite.position.set(35, 50, railLength / 2);
		eveningSprite.scale.set(12, 3, 1);
		scene.add(eveningSprite);
		
		// === CENTRAL TIMELINE RAIL (noon line, more prominent) ===
		const railGeometry = new THREE.BufferGeometry().setFromPoints([
			new THREE.Vector3(0, 0.1, -20),
			new THREE.Vector3(0, 0.1, railLength)
		]);
		const railMaterial = new THREE.LineBasicMaterial({ color: 0x00ffff, transparent: true, opacity: 0.5 });
		scene.add(new THREE.Line(railGeometry, railMaterial));
		
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
				
				// Date label sprite - positioned high above buildings (max height is 80)
				const dateLabel = getDateLabel(timestamp);
				const labelSprite = createTextSprite(THREE, dateLabel, markerColor);
				labelSprite.position.set(-35, 95, z);
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
		const particleCount = 4000;
		const particlesGeometry = new THREE.BufferGeometry();
		const positions = new Float32Array(particleCount * 3);
		const colors = new Float32Array(particleCount * 3);
		const velocities: number[] = [];
		
		for (let i = 0; i < particleCount; i++) {
			positions[i * 3] = (Math.random() - 0.5) * 300;
			positions[i * 3 + 1] = Math.random() * 100;
			positions[i * 3 + 2] = (Math.random() - 0.5) * 300;
			
			velocities.push(
				(Math.random() - 0.5) * 0.8,
				(Math.random() - 0.5) * 0.3,
				(Math.random() - 0.5) * 0.8
			);
			
			const colorChoice = Math.random();
			if (colorChoice < 0.4) {
				colors[i * 3] = 0; colors[i * 3 + 1] = 1; colors[i * 3 + 2] = 1;
			} else if (colorChoice < 0.7) {
				colors[i * 3] = 1; colors[i * 3 + 1] = 0; colors[i * 3 + 2] = 1;
			} else {
				colors[i * 3] = 0; colors[i * 3 + 1] = 0.5; colors[i * 3 + 2] = 1;
			}
		}
		
		particlesGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
		particlesGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
		
		const particlesMaterial = new THREE.PointsMaterial({
			size: 0.25,
			transparent: true,
			opacity: 0.9,
			vertexColors: true,
			blending: THREE.AdditiveBlending
		});
		
		const particles = new THREE.Points(particlesGeometry, particlesMaterial);
		particles.userData.velocities = velocities;
		scene.add(particles);
		scene.userData.particles = particles;
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
		
		// Animate flying particles - follow camera
		if (scene.userData.particles) {
			const positions = scene.userData.particles.geometry.attributes.position.array;
			const velocities = scene.userData.particles.userData.velocities;
			
			for (let i = 0; i < positions.length / 3; i++) {
				positions[i * 3] += velocities[i * 3];
				positions[i * 3 + 1] += velocities[i * 3 + 1];
				positions[i * 3 + 2] += velocities[i * 3 + 2];
				
				// Wrap around camera position
				const relX = positions[i * 3] - cameraWorldPos.x;
				const relZ = positions[i * 3 + 2] - cameraWorldPos.z;
				
				if (Math.abs(relX) > 150) positions[i * 3] = cameraWorldPos.x - relX * 0.5;
				if (positions[i * 3 + 1] < 0) positions[i * 3 + 1] = 100;
				if (positions[i * 3 + 1] > 100) positions[i * 3 + 1] = 0;
				if (Math.abs(relZ) > 150) positions[i * 3 + 2] = cameraWorldPos.z - relZ * 0.5;
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
	
	const initGestureControl = async () => {
		await enumerateVideoDevices();
		
		gestureController = new MediaPipeGestureController();
		await gestureController.initialize(videoElement, gestureCanvas);
		await gestureController.startCamera(selectedDeviceId || undefined);
		
		// ☝️ POINTING = TURBO forward into the past (older chats)
		gestureController.on('Pointing_Up', () => {
			currentGesture = '☝️ TURBO → Past!';
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
		
		// ✊ FIST = Fly backward toward NOW (newer chats)
		gestureController.on('Closed_Fist', () => {
			currentGesture = '✊ BACK ← Now!';
			cameraTarget.z -= 25; // Backward along timeline (toward newer)
		});
		
		// ✌️ VICTORY = Ascend for overview
		gestureController.on('Victory', () => {
			currentGesture = '✌️ OVERVIEW - Bird\'s eye!';
			cameraTarget.y = Math.min(120, cameraTarget.y + 15);
		});
		
		// 👍 THUMBS UP = Strafe to evening chats (right)
		gestureController.on('Thumb_Up', () => {
			currentGesture = '👍 → Evening chats';
			cameraTarget.x += 15;
		});
		
		// 👎 THUMBS DOWN = Strafe to morning chats (left)
		gestureController.on('Thumb_Down', () => {
			currentGesture = '👎 ← Morning chats';
			cameraTarget.x -= 15;
		});
		
		// 🤟 I LOVE YOU = Warp to next chat along timeline
		gestureController.on('ILoveYou', () => {
			const chatBuildingArray = Array.from(chatBuildings.values());
			if (chatBuildingArray.length > 0) {
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
			gestureMode = false;
			currentGesture = '';
		}
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
				currentGesture = `🎯 Selected: ${building.userData.chatTitle}`;
				
				// Clear gesture message after 2 seconds
				setTimeout(() => {
					if (currentGesture.startsWith('🎯')) currentGesture = '';
				}, 2000);
			}
		} else {
			// Clicked empty space - deselect
			selectedChatBuilding = null;
		}
	};
	
	onMount(async () => {
		await initThreeJS();
		
		window.addEventListener('resize', () => {
			if (camera && renderer) {
				camera.aspect = window.innerWidth / window.innerHeight;
				camera.updateProjectionMatrix();
				renderer.setSize(window.innerWidth, window.innerHeight);
			}
		});
	});
	
	onDestroy(() => {
		if (animationId) {
			cancelAnimationFrame(animationId);
		}
		
		if (gestureController) {
			gestureController.dispose();
		}
		
		if (renderer) {
			renderer.dispose();
		}
	});
</script>

<div class="theater-container" bind:this={container}>
	<canvas 
		bind:this={sceneCanvas}
		class="scene-canvas"
		on:wheel={handleWheel}
		on:mousemove={handleMouseMove}
		on:click={handleClick}
	></canvas>
	
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
						<span class="value">{userChats.length}</span>
					</div>
					<div class="stat">
						<span class="label">ALTITUDE:</span>
						<span class="value">{cameraTarget.y.toFixed(0)}m</span>
					</div>
				</div>
				<div class="timeline-hint">
					<div>◀ NOW — scroll forward — PAST ▶</div>
				</div>
			{/if}
			
			{#if currentGesture}
				<div class="gesture-feedback">
					{currentGesture}
				</div>
			{/if}
		</div>
		
		<div class="bottom-controls">
			<button 
				class="control-btn" 
				class:active={gestureMode}
				on:click={toggleGestureMode}
			>
				{gestureMode ? '🤚 JACKED IN' : '👋 JACK IN'}
			</button>
			
			<div class="help-text">
				{#if gestureMode}
					<div>☝️ Point → Past | ✊ Fist ← Now | ✋ Palm = Select</div>
					<div>✌️ Overview | 👍 Evening 👎 Morning | 🤟 Warp Next</div>
				{:else}
					<div>🖱️ Drag = Strafe | 🔄 Scroll = Timeline | 🖱️ Click = Select chat</div>
				{/if}
			</div>
		</div>
	</div>
	
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
	.theater-container {
		position: relative;
		width: 100%;
		height: 100%;
		overflow: hidden;
	}
	
	.scene-canvas {
		display: block;
		width: 100%;
		height: 100%;
		cursor: grab;
	}
	
	.scene-canvas:active {
		cursor: grabbing;
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
</style>
