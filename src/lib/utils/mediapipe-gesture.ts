import { GestureRecognizer, FaceLandmarker, FilesetResolver, DrawingUtils } from '@mediapipe/tasks-vision';

export type GestureType = 
  | 'Thumb_Up' 
  | 'Thumb_Down' 
  | 'Victory' 
  | 'Open_Palm' 
  | 'Closed_Fist'
  | 'Pointing_Up'
  | 'ILoveYou';

// Dual-hand combo gestures
export type DualGestureType =
  | 'Dual_Pointing'    // Both hands pointing = finger guns = fly forward fast
  | 'Dual_Open_Palm';  // Both hands open palm = halt

export type AllGestureTypes = GestureType | DualGestureType;

export type GestureCallback = (gesture: AllGestureTypes, handedness: string) => void;

export type FaceLandmarkCallback = (landmarks: any[], blendShapes: any[]) => void;

export type HandLandmarkCallback = (landmarks: any[], handednesses: any[]) => void;

export class MediaPipeGestureController {
  private gestureRecognizer: GestureRecognizer | null = null;
  private faceLandmarker: FaceLandmarker | null = null;
  private video: HTMLVideoElement | null = null;
  private canvasElement: HTMLCanvasElement | null = null;
  private canvasCtx: CanvasRenderingContext2D | null = null;
  private stream: MediaStream | null = null;
  private animationFrameId: number | null = null;
  private callbacks: Map<AllGestureTypes, GestureCallback[]> = new Map();
  private lastGestureTime: Map<AllGestureTypes, number> = new Map();
  private gestureDebounceMs = 300;
  
  // Track current gestures for each hand
  private leftHandGesture: GestureType | null = null;
  private rightHandGesture: GestureType | null = null;
  private lastDualGestureTime = 0;
  private dualGestureDebounceMs = 200;
  
  // Face landmark callbacks
  private faceLandmarkCallbacks: FaceLandmarkCallback[] = [];
  
  // Hand landmark callbacks
  private handLandmarkCallbacks: HandLandmarkCallback[] = [];
  
  async initialize(videoElement: HTMLVideoElement, canvasElement: HTMLCanvasElement): Promise<void> {
    this.video = videoElement;
    this.canvasElement = canvasElement;
    this.canvasCtx = canvasElement.getContext('2d');
    
    const vision = await FilesetResolver.forVisionTasks(
      'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.17/wasm'
    );
    
    this.gestureRecognizer = await GestureRecognizer.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task',
        delegate: 'GPU'
      },
      runningMode: 'VIDEO',
      numHands: 2,
      minHandDetectionConfidence: 0.5,
      minHandPresenceConfidence: 0.5,
      minTrackingConfidence: 0.5
    });
    
    // Initialize face landmarker
    this.faceLandmarker = await FaceLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
        delegate: 'GPU'
      },
      runningMode: 'VIDEO',
      numFaces: 1,
      outputFaceBlendshapes: true,
      outputFacialTransformationMatrixes: true
    });
  }
  
  async startCamera(deviceId?: string): Promise<void> {
    if (!this.video) {
      throw new Error('Video element not initialized');
    }
    
    const videoConstraints: MediaTrackConstraints = {
      width: 1280,
      height: 720
    };
    
    if (deviceId) {
      videoConstraints.deviceId = { exact: deviceId };
    } else {
      videoConstraints.facingMode = 'user';
    }
    
    this.stream = await navigator.mediaDevices.getUserMedia({
      video: videoConstraints
    });
    
    this.video.srcObject = this.stream;
    await this.video.play();
    
    if (this.canvasElement) {
      this.canvasElement.width = this.video.videoWidth;
      this.canvasElement.height = this.video.videoHeight;
    }
    
    this.startDetection();
  }
  
  private startDetection(): void {
    const detect = async () => {
      if (!this.video || !this.gestureRecognizer || !this.canvasCtx || !this.canvasElement) {
        return;
      }
      
      if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
        const nowInMs = Date.now();
        const results = this.gestureRecognizer.recognizeForVideo(this.video, nowInMs);
        
        // Face landmark detection
        if (this.faceLandmarker && this.faceLandmarkCallbacks.length > 0) {
          const faceResults = this.faceLandmarker.detectForVideo(this.video, nowInMs);
          if (faceResults.faceLandmarks && faceResults.faceLandmarks.length > 0) {
            const blendShapes = faceResults.faceBlendshapes?.[0]?.categories || [];
            this.faceLandmarkCallbacks.forEach(cb => cb(faceResults.faceLandmarks, blendShapes));
          }
        }
        
        this.canvasCtx.save();
        this.canvasCtx.clearRect(0, 0, this.canvasElement.width, this.canvasElement.height);
        
        if (results.landmarks) {
          // Invoke hand landmark callbacks
          if (this.handLandmarkCallbacks.length > 0 && results.landmarks.length > 0) {
            this.handLandmarkCallbacks.forEach(cb => cb(results.landmarks, results.handednesses || []));
          }
          
          for (const landmarks of results.landmarks) {
            const drawingUtils = new DrawingUtils(this.canvasCtx);
            drawingUtils.drawConnectors(landmarks, GestureRecognizer.HAND_CONNECTIONS, {
              color: '#00FF00',
              lineWidth: 3
            });
            drawingUtils.drawLandmarks(landmarks, {
              color: '#FF0000',
              lineWidth: 1,
              radius: 3
            });
          }
        }
        
        // Reset hand gestures each frame
        this.leftHandGesture = null;
        this.rightHandGesture = null;
        
        if (results.gestures && results.gestures.length > 0) {
          for (let i = 0; i < results.gestures.length; i++) {
            const gesture = results.gestures[i][0];
            const handedness = results.handednesses[i][0];
            
            if (gesture && gesture.score > 0.7) {
              const gestureName = gesture.categoryName as GestureType;
              
              // Track which hand has which gesture
              if (handedness.categoryName === 'Left') {
                this.leftHandGesture = gestureName;
              } else {
                this.rightHandGesture = gestureName;
              }
              
              // Still trigger single-hand gestures
              this.triggerGesture(gestureName, handedness.categoryName);
            }
          }
          
          // Check for dual-hand gestures
          this.checkDualGestures();
        }
        
        this.canvasCtx.restore();
      }
      
      this.animationFrameId = requestAnimationFrame(detect);
    };
    
    detect();
  }
  
  private checkDualGestures(): void {
    const now = Date.now();
    
    // Check if both hands are detected
    if (this.leftHandGesture && this.rightHandGesture) {
      // Dual Pointing (finger guns) - both hands pointing up
      if (this.leftHandGesture === 'Pointing_Up' && this.rightHandGesture === 'Pointing_Up') {
        this.triggerDualGesture('Dual_Pointing');
      }
      
      // Dual Open Palm - both hands flat
      if (this.leftHandGesture === 'Open_Palm' && this.rightHandGesture === 'Open_Palm') {
        this.triggerDualGesture('Dual_Open_Palm');
      }
    }
  }
  
  private triggerDualGesture(gesture: DualGestureType): void {
    const now = Date.now();
    
    if (now - this.lastDualGestureTime < this.dualGestureDebounceMs) {
      return;
    }
    
    this.lastDualGestureTime = now;
    this.lastGestureTime.set(gesture, now);
    
    const callbacks = this.callbacks.get(gesture);
    if (callbacks) {
      callbacks.forEach(cb => cb(gesture, 'Both'));
    }
  }
  
  private triggerGesture(gesture: GestureType, handedness: string): void {
    const now = Date.now();
    const lastTime = this.lastGestureTime.get(gesture) || 0;
    
    if (now - lastTime < this.gestureDebounceMs) {
      return;
    }
    
    this.lastGestureTime.set(gesture, now);
    
    const callbacks = this.callbacks.get(gesture);
    if (callbacks) {
      callbacks.forEach(cb => cb(gesture, handedness));
    }
  }
  
  on(gesture: AllGestureTypes, callback: GestureCallback): void {
    if (!this.callbacks.has(gesture)) {
      this.callbacks.set(gesture, []);
    }
    this.callbacks.get(gesture)!.push(callback);
  }
  
  // Register callback for a gesture performed by a specific hand
  onWithHand(gesture: GestureType, hand: 'Left' | 'Right', callback: () => void): void {
    this.on(gesture, (g, handedness) => {
      if (handedness === hand) {
        callback();
      }
    });
  }
  
  off(gesture: AllGestureTypes, callback?: GestureCallback): void {
    if (!callback) {
      this.callbacks.delete(gesture);
      return;
    }
    
    const callbacks = this.callbacks.get(gesture);
    if (callbacks) {
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }
  
  onFaceLandmarks(callback: FaceLandmarkCallback): void {
    this.faceLandmarkCallbacks.push(callback);
  }
  
  offFaceLandmarks(callback?: FaceLandmarkCallback): void {
    if (!callback) {
      this.faceLandmarkCallbacks = [];
      return;
    }
    const index = this.faceLandmarkCallbacks.indexOf(callback);
    if (index > -1) {
      this.faceLandmarkCallbacks.splice(index, 1);
    }
  }
  
  onHandLandmarks(callback: HandLandmarkCallback): void {
    this.handLandmarkCallbacks.push(callback);
  }
  
  offHandLandmarks(callback?: HandLandmarkCallback): void {
    if (!callback) {
      this.handLandmarkCallbacks = [];
      return;
    }
    const index = this.handLandmarkCallbacks.indexOf(callback);
    if (index > -1) {
      this.handLandmarkCallbacks.splice(index, 1);
    }
  }
  
  stopCamera(): void {
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    
    if (this.video) {
      this.video.srcObject = null;
    }
  }
  
  dispose(): void {
    this.stopCamera();
    this.callbacks.clear();
    this.lastGestureTime.clear();
    this.faceLandmarkCallbacks = [];
    
    if (this.gestureRecognizer) {
      this.gestureRecognizer.close();
      this.gestureRecognizer = null;
    }
    
    if (this.faceLandmarker) {
      this.faceLandmarker.close();
      this.faceLandmarker = null;
    }
  }
}
