<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { chats, chatId } from '$lib/stores';
	import { MediaPipeGestureController, type GestureType, type DualGestureType, type AllGestureTypes } from '$lib/utils/mediapipe-gesture';
	
	export let onClose: () => void;
	
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
	const BUILDINGS_PER_CHUNK = 15;
	let loadedChunks: Map<string, any> = new Map();
	let threeRef: any = null;
	
	// Seeded random for consistent chunk generation
	const seededRandom = (seed: number) => {
		const x = Math.sin(seed * 12.9898 + seed * 78.233) * 43758.5453;
		return x - Math.floor(x);
	};
	
	const getChunkKey = (cx: number, cz: number) => `${cx},${cz}`;
	
	const createChatGraph = (THREE: any) => {
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
		
		// Initial chunk loading
		updateChunks();
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
		const chunkSeed = chunkX * 10000 + chunkZ;
		const chunkBuildings: any[] = [];
		
		// Ground grid for this chunk
		const gridHelper = new THREE.GridHelper(CHUNK_SIZE, 20, 0x00ffff, 0x002233);
		gridHelper.position.set(chunkX * CHUNK_SIZE, 0, chunkZ * CHUNK_SIZE);
		chunkGroup.add(gridHelper);
		
		// Elevated grid
		const gridHelper2 = new THREE.GridHelper(CHUNK_SIZE, 10, 0xff00ff, 0x220022);
		gridHelper2.position.set(chunkX * CHUNK_SIZE, 70, chunkZ * CHUNK_SIZE);
		gridHelper2.material.opacity = 0.2;
		gridHelper2.material.transparent = true;
		chunkGroup.add(gridHelper2);
		
		// Generate buildings for this chunk
		for (let i = 0; i < BUILDINGS_PER_CHUNK; i++) {
			const seed = chunkSeed + i * 137;
			const localX = (seededRandom(seed) - 0.5) * (CHUNK_SIZE - 10);
			const localZ = (seededRandom(seed + 1) - 0.5) * (CHUNK_SIZE - 10);
			const worldX = chunkX * CHUNK_SIZE + localX;
			const worldZ = chunkZ * CHUNK_SIZE + localZ;
			
			const building = createProceduralBuilding(THREE, seed, worldX, worldZ);
			chunkGroup.add(building);
			chunkBuildings.push(building);
		}
		
		// Create highways within chunk
		for (let i = 0; i < chunkBuildings.length; i++) {
			const connectCount = Math.floor(seededRandom(chunkSeed + i * 500) * 2) + 1;
			for (let c = 0; c < connectCount; c++) {
				const targetIdx = Math.floor(seededRandom(chunkSeed + i * 500 + c) * chunkBuildings.length);
				if (targetIdx !== i) {
					const highway = createDataHighway(THREE, chunkBuildings[i], chunkBuildings[targetIdx]);
					if (highway) chunkGroup.add(highway.group);
				}
			}
		}
		
		chunkGroup.userData = { chunkX, chunkZ, buildings: chunkBuildings };
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
		const geometry = new THREE.BoxGeometry(width, height, width);
		const edges = new THREE.EdgesGeometry(geometry);
		const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.8 }));
		line.position.y = height / 2;
		group.add(line);
		
		const coreGeometry = new THREE.BoxGeometry(width - 0.5, height - 1, width - 0.5);
		const coreMaterial = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.2 });
		const core = new THREE.Mesh(coreGeometry, coreMaterial);
		core.position.y = height / 2;
		group.add(core);
	};
	
	const createPyramidTower = (THREE: any, group: any, height: number, width: number, color: number, altColor: number) => {
		const segments = 4;
		for (let i = 0; i < segments; i++) {
			const segHeight = height / segments;
			const segWidth = width * (1 - i * 0.2);
			const geometry = new THREE.BoxGeometry(segWidth, segHeight, segWidth);
			const edges = new THREE.EdgesGeometry(geometry);
			const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ 
				color: i % 2 === 0 ? color : altColor, transparent: true, opacity: 0.7 
			}));
			line.position.y = i * segHeight + segHeight / 2;
			group.add(line);
		}
	};
	
	const createCylinderTower = (THREE: any, group: any, height: number, width: number, color: number) => {
		const geometry = new THREE.CylinderGeometry(width / 2, width / 2, height, 12);
		const edges = new THREE.EdgesGeometry(geometry);
		const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.8 }));
		line.position.y = height / 2;
		group.add(line);
		
		const coreGeometry = new THREE.CylinderGeometry(width / 2 - 0.3, width / 2 - 0.3, height - 1, 12);
		const coreMaterial = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.15 });
		const core = new THREE.Mesh(coreGeometry, coreMaterial);
		core.position.y = height / 2;
		group.add(core);
	};
	
	const createStackedTower = (THREE: any, group: any, height: number, width: number, color: number, altColor: number, seed: number) => {
		const blocks = Math.floor(seededRandom(seed + 500) * 4) + 3;
		let currentY = 0;
		for (let i = 0; i < blocks; i++) {
			const blockHeight = height / blocks + (seededRandom(seed + i * 77) - 0.5) * 5;
			const blockWidth = width * (0.7 + seededRandom(seed + i * 88) * 0.6);
			const geometry = new THREE.BoxGeometry(blockWidth, blockHeight, blockWidth);
			const edges = new THREE.EdgesGeometry(geometry);
			const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ 
				color: i % 2 === 0 ? color : altColor, transparent: true, opacity: 0.7 
			}));
			line.position.y = currentY + blockHeight / 2;
			line.rotation.y = seededRandom(seed + i * 99) * Math.PI / 4;
			group.add(line);
			currentY += blockHeight;
		}
	};
	
	const createSpireTower = (THREE: any, group: any, height: number, width: number, color: number, altColor: number) => {
		// Base
		const baseGeometry = new THREE.BoxGeometry(width * 1.5, height * 0.3, width * 1.5);
		const baseEdges = new THREE.EdgesGeometry(baseGeometry);
		const baseLine = new THREE.LineSegments(baseEdges, new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.8 }));
		baseLine.position.y = height * 0.15;
		group.add(baseLine);
		
		// Spire
		const spireGeometry = new THREE.ConeGeometry(width / 2, height * 0.7, 6);
		const spireEdges = new THREE.EdgesGeometry(spireGeometry);
		const spireLine = new THREE.LineSegments(spireEdges, new THREE.LineBasicMaterial({ color: altColor, transparent: true, opacity: 0.8 }));
		spireLine.position.y = height * 0.3 + height * 0.35;
		group.add(spireLine);
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
		
		// ☝️ POINTING = TURBO FLY FORWARD
		gestureController.on('Pointing_Up', () => {
			currentGesture = '☝️ TURBO - Maximum velocity!';
			cameraTarget.z -= 60;
			cameraTarget.y = Math.max(12, cameraTarget.y - 1);
		});
		
		// ✋ OPEN PALM = HALT
		gestureController.on('Open_Palm', () => {
			currentGesture = '✋ HALT - Hovering...';
			flySpeed = 0;
		});
		
		// ✊ FIST = Normal fly forward
		gestureController.on('Closed_Fist', () => {
			currentGesture = '✊ FLY - Jacking deeper!';
			cameraTarget.z -= 12;
		});
		
		// ✌️ VICTORY = Ascend
		gestureController.on('Victory', () => {
			currentGesture = '✌️ ASCEND - Rising up!';
			cameraTarget.y = Math.min(80, cameraTarget.y + 8);
		});
		
		// 👍 THUMBS UP = Strafe right
		gestureController.on('Thumb_Up', () => {
			currentGesture = '👍 STRAFE RIGHT';
			cameraTarget.x += 12;
		});
		
		// 👎 THUMBS DOWN = Strafe left
		gestureController.on('Thumb_Down', () => {
			currentGesture = '👎 STRAFE LEFT';
			cameraTarget.x -= 12;
		});
		
		// 🤟 I LOVE YOU = Warp to system
		gestureController.on('ILoveYou', () => {
			currentGesture = '🤟 WARP - Teleporting!';
			if (buildings.length > 0) {
				const nearbyBuildings = buildings.filter((b: any) => {
					const dx = b.position.x - cameraWorldPos.x;
					const dz = b.position.z - cameraWorldPos.z;
					return Math.sqrt(dx*dx + dz*dz) < CHUNK_SIZE * 2;
				});
				if (nearbyBuildings.length > 0) {
					const target = nearbyBuildings[Math.floor(Math.random() * nearbyBuildings.length)];
					cameraTarget.x = target.position.x;
					cameraTarget.z = target.position.z + 20;
					cameraTarget.y = target.userData.height + 10;
					zoom = 30;
				}
			}
		});
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
			<div class="info-text">
				<div class="stat">
					<span class="label">SECTOR:</span>
					<span class="value">{Math.floor(cameraWorldPos.x / CHUNK_SIZE)},{Math.floor(cameraWorldPos.z / CHUNK_SIZE)}</span>
				</div>
				<div class="stat">
					<span class="label">LOADED CHUNKS:</span>
					<span class="value">{loadedChunks.size}</span>
				</div>
				<div class="stat">
					<span class="label">DATA TOWERS:</span>
					<span class="value">{buildings.length}</span>
				</div>
				<div class="stat">
					<span class="label">ALTITUDE:</span>
					<span class="value">{cameraTarget.y.toFixed(0)}m</span>
				</div>
				<div class="stat">
					<span class="label">POSITION:</span>
					<span class="value">{cameraWorldPos.x.toFixed(0)}, {cameraWorldPos.z.toFixed(0)}</span>
				</div>
			</div>
			
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
					<div>☝️ Point = TURBO | ✋ Palm = HALT | ✊ Fist = Fly</div>
					<div>✌️ Ascend | 👍👎 Strafe | 🤟 Warp</div>
				{:else}
					<div>🖱️ Drag to Strafe | 🔄 Scroll to Fly | The grid extends infinitely...</div>
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
		box-shadow: 0 0 20px rgba(0, 255, 255, 0.3), inset 0 0 20px rgba(255, 0, 255, 0.1);
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
