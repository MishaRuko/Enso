"use client";

import {
  Component,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Canvas, useThree, useLoader } from "@react-three/fiber";
import { OrbitControls, Environment, Grid, ContactShadows, useGLTF } from "@react-three/drei";
import type * as THREE from "three";
import { Box3, Color, MeshStandardMaterial, Plane, Raycaster, Vector2, Vector3 } from "three";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import { EnsoSpinner } from "@/components/enso-logo";
import { ProceduralRoom } from "@/components/procedural-room";
import { FurnitureModel } from "@/components/furniture-model";
import type { RoomData, FurnitureItem, FurniturePlacement } from "@/lib/types";

const BG_COLOR = new Color("#faf9f7");

class ViewerErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; error: string }
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: "" };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: "100%",
            color: "var(--muted)",
            flexDirection: "column",
            gap: "0.5rem",
          }}
        >
          <p>3D Viewer encountered an error</p>
          <p style={{ fontSize: "0.75rem", opacity: 0.6 }}>{this.state.error}</p>
        </div>
      );
    }
    return this.props.children;
  }
}

interface RoomViewerProps {
  roomData?: RoomData;
  roomGlbUrl?: string | null;
  allRooms?: RoomData[];
  placements?: FurniturePlacement[];
  furnitureItems?: FurnitureItem[];
  floorplanUrl?: string | null;
  onPlacementChange?: (placements: FurniturePlacement[]) => void;
}

/**
 * Detect the floor level of a Trellis-generated GLB by analysing vertex density
 * along the Y axis. The floor slab is a dense horizontal band of vertices —
 * we find the bottom of that band and clip just below it. If the geometry is
 * clean (no artifacts hanging below), no clipping is applied.
 */
function detectFloorClipY(root: THREE.Object3D): number | null {
  const ys: number[] = [];
  root.traverse((child) => {
    if ("geometry" in child) {
      const geo = (child as THREE.Mesh).geometry;
      const pos = geo?.attributes?.position;
      if (!pos) return;
      // Sample every 4th vertex for performance on dense meshes
      for (let i = 0; i < pos.count; i += 4) {
        ys.push(pos.getY(i));
      }
    }
  });

  if (ys.length < 20) return null;

  ys.sort((a, b) => a - b);

  const box = new Box3().setFromObject(root);
  const totalHeight = box.max.y - box.min.y;
  if (totalHeight < 0.01) return null;

  // Build a histogram of vertex Y positions (40 bins)
  const bins = 40;
  const binSize = totalHeight / bins;
  const counts = new Array<number>(bins).fill(0);
  for (const y of ys) {
    const idx = Math.min(Math.floor((y - box.min.y) / binSize), bins - 1);
    counts[idx]++;
  }

  // Find the densest bin in the bottom half — that's the floor slab
  const halfBins = Math.floor(bins / 2);
  let maxCount = 0;
  let floorBin = -1;
  for (let i = 0; i < halfBins; i++) {
    if (counts[i] > maxCount) {
      maxCount = counts[i];
      floorBin = i;
    }
  }

  if (floorBin < 0) return null;

  // Check if there are significant vertices below the floor slab
  let belowCount = 0;
  for (let i = 0; i < floorBin; i++) {
    belowCount += counts[i];
  }

  // If less than 5% of vertices are below the floor, no clipping needed
  if (belowCount < ys.length * 0.05) return null;

  // Clip at the bottom edge of the floor bin (preserve the floor itself)
  return box.min.y + floorBin * binSize;
}

function isObjUrl(url: string): boolean {
  return /\.obj(\?|$)/i.test(url);
}

const DEFAULT_ROOM_MAT = new MeshStandardMaterial({
  color: 0xd4c8bc,
  roughness: 0.85,
  metalness: 0.05,
});

function applyFloorClip(root: THREE.Object3D) {
  const clipY = detectFloorClipY(root);
  if (clipY !== null) {
    const clipPlane = new Plane(new Vector3(0, 1, 0), -clipY);
    root.traverse((child) => {
      if ("material" in child && child.material) {
        const mats = Array.isArray(child.material) ? child.material : [child.material];
        for (const mat of mats) {
          mat.clippingPlanes = [clipPlane];
          mat.clipShadows = true;
        }
      }
    });
  }
}

function RoomOBJModel({ url, onLoaded }: { url: string; onLoaded?: () => void }) {
  const obj = useLoader(OBJLoader, url);
  const cloned = useMemo(() => {
    const c = obj.clone();
    // OBJ files from fal.ai often lack materials — apply a default
    c.traverse((child) => {
      if ("isMesh" in child && (child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh;
        if (!mesh.material || (mesh.material as THREE.MeshStandardMaterial).name === "") {
          mesh.material = DEFAULT_ROOM_MAT;
        }
        mesh.castShadow = true;
        mesh.receiveShadow = true;
      }
    });
    applyFloorClip(c);
    return c;
  }, [obj]);

  if (onLoaded) {
    queueMicrotask(onLoaded);
  }
  return <primitive object={cloned} />;
}

function RoomGLBModel({
  url,
  roomData,
  allRooms,
  onLoaded,
}: {
  url: string;
  roomData?: RoomData;
  allRooms?: RoomData[];
  onLoaded?: () => void;
}) {
  const { scene } = useGLTF(url);
  const cloned = useMemo(() => {
    const c = scene.clone();
    applyFloorClip(c);

    // Auto-scale Trellis GLB to match room/apartment dimensions.
    // When multiple rooms exist, the GLB is the full apartment —
    // compute the actual footprint from room positions + sizes.
    if (roomData) {
      const box = new Box3().setFromObject(c);
      const size = new Vector3();
      box.getSize(size);

      if (size.x > 0.01 && size.z > 0.01) {
        let targetW = roomData.width_m;
        let targetL = roomData.length_m;

        if (allRooms && allRooms.length > 1) {
          let maxX = 0;
          let maxZ = 0;
          for (const r of allRooms) {
            maxX = Math.max(maxX, (r.x_offset_m ?? 0) + r.width_m);
            maxZ = Math.max(maxZ, (r.z_offset_m ?? 0) + r.length_m);
          }
          targetW = maxX;
          targetL = maxZ;
        }

        // Non-uniform X/Z scaling to match exact apartment footprint
        const sX = targetW / size.x;
        const sZ = targetL / size.z;
        const sY = Math.max(sX, sZ);
        c.scale.set(sX, sY, sZ);

        const scaledBox = new Box3().setFromObject(c);
        c.position.y -= scaledBox.min.y;
        c.position.x -= scaledBox.min.x;
        c.position.z -= scaledBox.min.z;
      }
    }

    return c;
  }, [scene, roomData, allRooms]);

  if (onLoaded) {
    queueMicrotask(onLoaded);
  }
  return <primitive object={cloned} receiveShadow castShadow />;
}

function SceneBackground() {
  const { scene, gl } = useThree();
  scene.background = BG_COLOR;
  gl.localClippingEnabled = true;
  return null;
}

// --- Drag logic ---

interface DragState {
  itemId: string;
  offsetX: number;
  offsetZ: number;
}

function DragPlane({
  dragState,
  onDrag,
  onDragEnd,
}: {
  dragState: DragState | null;
  onDrag: (x: number, z: number) => void;
  onDragEnd: () => void;
}) {
  const { camera, gl } = useThree();
  const raycaster = useMemo(() => new Raycaster(), []);
  const floorPlane = useMemo(() => new Plane(new Vector3(0, 1, 0), 0), []);
  const mouse = useMemo(() => new Vector2(), []);
  const intersection = useMemo(() => new Vector3(), []);

  // Keep stable refs for callbacks to avoid stale closures
  const onDragRef = useRef(onDrag);
  const onDragEndRef = useRef(onDragEnd);
  onDragRef.current = onDrag;
  onDragEndRef.current = onDragEnd;

  useEffect(() => {
    if (!dragState) return;

    const canvas = gl.domElement;

    const getWorldPoint = (e: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);
      raycaster.ray.intersectPlane(floorPlane, intersection);
      return intersection;
    };

    const handleMove = (e: PointerEvent) => {
      const pt = getWorldPoint(e);
      if (pt) {
        onDragRef.current(pt.x - dragState.offsetX, pt.z - dragState.offsetZ);
      }
    };

    const handleUp = () => {
      onDragEndRef.current();
      document.body.style.cursor = "auto";
    };

    document.body.style.cursor = "grabbing";
    canvas.addEventListener("pointermove", handleMove);
    canvas.addEventListener("pointerup", handleUp);
    return () => {
      canvas.removeEventListener("pointermove", handleMove);
      canvas.removeEventListener("pointerup", handleUp);
    };
  }, [dragState, camera, gl, raycaster, floorPlane, mouse, intersection]);

  return null;
}

interface SceneProps extends RoomViewerProps {
  onGlbLoaded?: () => void;
}

function Scene({
  roomData,
  roomGlbUrl,
  allRooms,
  placements,
  furnitureItems,
  onGlbLoaded,
  onPlacementChange,
}: SceneProps) {
  const itemMap = new Map<string, FurnitureItem>();
  if (furnitureItems) {
    for (const item of furnitureItems) {
      itemMap.set(item.id, item);
    }
  }

  const hasRoomGlb = !!roomGlbUrl;
  // biome-ignore lint/suspicious/noExplicitAny: drei OrbitControls ref type
  const controlsRef = useRef<any>(null);
  const [dragState, setDragState] = useState<DragState | null>(null);

  // Keep a stable ref to placements for use in callbacks
  const placementsRef = useRef(placements);
  placementsRef.current = placements;
  const onChangeRef = useRef(onPlacementChange);
  onChangeRef.current = onPlacementChange;

  const handleDragStart = useCallback((itemId: string, point: Vector3) => {
    const pls = placementsRef.current;
    if (!pls || !onChangeRef.current) return;
    const p = pls.find((pl) => pl.item_id === itemId);
    if (!p) return;
    setDragState({
      itemId,
      offsetX: point.x - p.position.x,
      offsetZ: point.z - p.position.z,
    });
    const ctrl = controlsRef.current as any;
    if (ctrl) ctrl.enabled = false;
  }, []);

  const handleDrag = useCallback((x: number, z: number) => {
    const pls = placementsRef.current;
    const onChange = onChangeRef.current;
    if (!pls || !onChange) return;
    setDragState((ds) => {
      if (!ds) return null;
      const updated = pls.map((p) =>
        p.item_id === ds.itemId
          ? {
              ...p,
              position: {
                ...p.position,
                x: Math.round(x * 100) / 100,
                z: Math.round(z * 100) / 100,
              },
            }
          : p,
      );
      onChange(updated);
      return ds;
    });
  }, []);

  const handleDragEnd = useCallback(() => {
    setDragState(null);
    const ctrl = controlsRef.current as any;
    if (ctrl) ctrl.enabled = true;
  }, []);

  return (
    <>
      <SceneBackground />
      <ambientLight intensity={0.4} color="#faf9f7" />
      <directionalLight
        position={[5, 10, 4]}
        intensity={1.2}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-camera-far={30}
        shadow-camera-left={-10}
        shadow-camera-right={10}
        shadow-camera-top={10}
        shadow-camera-bottom={-10}
        shadow-bias={-0.001}
      />
      <directionalLight position={[-3, 6, -2]} intensity={0.3} color="#93c5fd" />
      <hemisphereLight intensity={0.3} color="#fef3c7" groundColor="#1e1b4b" />

      <Environment preset="apartment" />
      <OrbitControls
        ref={controlsRef}
        makeDefault
        enableDamping
        dampingFactor={0.08}
        minDistance={2}
        maxDistance={20}
        maxPolarAngle={Math.PI / 2.1}
      />

      <DragPlane dragState={dragState} onDrag={handleDrag} onDragEnd={handleDragEnd} />

      {/* Grid floor as fallback when no room data at all */}
      {!roomData && !hasRoomGlb && (
        <Grid
          args={[20, 20]}
          cellSize={0.5}
          cellThickness={0.5}
          cellColor="#ddd"
          sectionSize={2}
          sectionThickness={1}
          sectionColor="#1a1a38"
          fadeDistance={25}
          infiniteGrid
        />
      )}

      {/* Trellis-generated room model (GLB or OBJ) */}
      {hasRoomGlb && (
        <Suspense fallback={null}>
          {isObjUrl(roomGlbUrl!) ? (
            <RoomOBJModel url={roomGlbUrl!} onLoaded={onGlbLoaded} />
          ) : (
            <RoomGLBModel
              url={roomGlbUrl!}
              roomData={roomData}
              allRooms={allRooms}
              onLoaded={onGlbLoaded}
            />
          )}
        </Suspense>
      )}

      {/* Procedural room fallback when no GLB available */}
      {!hasRoomGlb && roomData && <ProceduralRoom roomData={roomData} />}

      {/* Contact shadows on the floor (only for procedural room) */}
      {roomData && !hasRoomGlb && (
        <ContactShadows
          position={[roomData.width_m / 2, 0.01, roomData.length_m / 2]}
          width={roomData.width_m * 1.2}
          height={roomData.length_m * 1.2}
          opacity={0.5}
          blur={2.5}
          far={4}
        />
      )}

      {/* Furniture models with GLB loading */}
      {placements?.map((p, i) => (
        <FurnitureModel
          key={`${p.item_id}-${i}`}
          placement={p}
          item={itemMap.get(p.item_id)}
          onDragStart={onPlacementChange ? handleDragStart : undefined}
          selected={dragState?.itemId === p.item_id}
        />
      ))}
    </>
  );
}

/**
 * Call from outside the Canvas/3D context to start fetching + parsing the
 * GLB in the background.  drei's useGLTF caches by URL, so when the
 * <RoomGLBModel> component mounts later it hits the warm cache instantly.
 */
export function preloadRoomGlb(url: string | null | undefined) {
  if (url && !isObjUrl(url)) useGLTF.preload(url);
}

export function RoomViewer({
  roomData,
  roomGlbUrl,
  allRooms,
  placements,
  furnitureItems,
  floorplanUrl,
  onPlacementChange,
}: RoomViewerProps) {
  // Kick off preload as early as possible
  useMemo(() => {
    preloadRoomGlb(roomGlbUrl);
  }, [roomGlbUrl]);

  // Camera should frame the full apartment footprint, not just the primary room
  const aptW =
    allRooms && allRooms.length > 1
      ? Math.max(...allRooms.map((r) => (r.x_offset_m ?? 0) + r.width_m))
      : (roomData?.width_m ?? 8);
  const aptL =
    allRooms && allRooms.length > 1
      ? Math.max(...allRooms.map((r) => (r.z_offset_m ?? 0) + r.length_m))
      : (roomData?.length_m ?? 8);
  const camX = aptW * 1.1;
  const camY = roomData ? Math.max(roomData.height_m * 1.8, 4) : 6;
  const camZ = aptL * 1.1;
  const [glbLoaded, setGlbLoaded] = useState(!roomGlbUrl);
  const showLoading = !!roomGlbUrl && !glbLoaded;
  const startRef = useRef(Date.now());
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!showLoading) return;
    const t = setInterval(() => setElapsed(Date.now() - startRef.current), 500);
    return () => clearInterval(t);
  }, [showLoading]);

  const handlePlacementChange = onPlacementChange
    ? (updated: FurniturePlacement[]) => {
        onPlacementChange(updated);
      }
    : undefined;

  const hasPlacements = placements && placements.length > 0;

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        background: "linear-gradient(180deg, #faf9f7 0%, #f3efe8 100%)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <ViewerErrorBoundary>
        <Canvas
          shadows
          camera={{ position: [camX, camY, camZ], fov: 45 }}
          style={{ width: "100%", height: "100%" }}
          gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}
        >
          <Scene
            roomData={roomData}
            roomGlbUrl={roomGlbUrl}
            allRooms={allRooms}
            placements={placements}
            furnitureItems={furnitureItems}
            onGlbLoaded={() => setGlbLoaded(true)}
            onPlacementChange={handlePlacementChange}
          />
        </Canvas>
      </ViewerErrorBoundary>

      {/* Loading overlay while GLB is fetching */}
      {showLoading &&
        (() => {
          const secs = Math.floor(elapsed / 1000);
          const m = Math.floor(secs / 60);
          const s = secs % 60;
          const timeStr = m > 0 ? `${m}m ${s}s` : `${s}s`;
          return (
            <div
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: "1.25rem",
                background: "linear-gradient(180deg, #faf9f7 0%, #f3efe8 100%)",
                zIndex: 5,
              }}
            >
              {floorplanUrl && (
                <img
                  src={floorplanUrl}
                  alt="Floorplan preview"
                  style={{
                    width: 180,
                    height: 130,
                    objectFit: "cover",
                    borderRadius: 10,
                    border: "1px solid rgba(26,26,56,0.08)",
                    opacity: 0.8,
                    animation: "fadeUp 0.5s ease-out",
                  }}
                />
              )}
              <EnsoSpinner size={40} />
              <div style={{ textAlign: "center" }}>
                <p
                  style={{
                    fontSize: "0.9375rem",
                    fontWeight: 600,
                    color: "#1a1a38",
                    marginBottom: "0.25rem",
                  }}
                >
                  Building 3D model
                </p>
                <p
                  style={{
                    color: "var(--muted)",
                    fontSize: "0.8125rem",
                    animation: "progressPulse 2s ease-in-out infinite",
                  }}
                >
                  {timeStr} elapsed
                </p>
              </div>
            </div>
          );
        })()}

      {/* Bottom controls hint */}
      <div
        style={{
          position: "absolute",
          bottom: "1rem",
          left: "50%",
          transform: "translateX(-50%)",
          display: "flex",
          gap: "1rem",
          padding: "0.375rem 1rem",
          borderRadius: "var(--radius-full)",
          background: "rgba(250,249,247,0.85)",
          backdropFilter: "blur(16px)",
          border: "1px solid rgba(236,230,219,0.5)",
          fontSize: "0.6875rem",
          color: "rgba(26,26,56,0.45)",
          letterSpacing: "0.02em",
          zIndex: 2,
          animation: "fadeIn 1s ease-out 0.5s both",
        }}
      >
        <span>
          {hasPlacements && onPlacementChange ? "Click furniture to drag" : "Drag to rotate"}
        </span>
        <span style={{ opacity: 0.3 }}>|</span>
        <span>Scroll to zoom</span>
        <span style={{ opacity: 0.3 }}>|</span>
        <span>Right-drag to pan</span>
      </div>
    </div>
  );
}
