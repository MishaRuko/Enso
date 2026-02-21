"use client";

import { Component, Suspense, type ReactNode } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment, Grid, ContactShadows, useGLTF } from "@react-three/drei";
import { ProceduralRoom } from "@/components/procedural-room";
import { FurnitureModel } from "@/components/furniture-model";
import type { RoomData, FurnitureItem, FurniturePlacement } from "@/lib/types";

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
  placements?: FurniturePlacement[];
  furnitureItems?: FurnitureItem[];
}

function RoomGLBModel({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  return <primitive object={scene.clone()} receiveShadow castShadow />;
}

function Scene({ roomData, roomGlbUrl, placements, furnitureItems }: RoomViewerProps) {
  const itemMap = new Map<string, FurnitureItem>();
  if (furnitureItems) {
    for (const item of furnitureItems) {
      itemMap.set(item.id, item);
    }
  }

  const hasRoomGlb = !!roomGlbUrl;

  return (
    <>
      {/* Lighting setup — warm ambient + strong directional with shadows */}
      <ambientLight intensity={0.4} color="#f5f0eb" />
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
        makeDefault
        enableDamping
        dampingFactor={0.08}
        minDistance={2}
        maxDistance={20}
        maxPolarAngle={Math.PI / 2.1}
      />

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

      {/* Trellis-generated room GLB model (preferred) */}
      {hasRoomGlb && (
        <Suspense fallback={roomData ? <ProceduralRoom roomData={roomData} /> : null}>
          <RoomGLBModel url={roomGlbUrl!} />
        </Suspense>
      )}

      {/* Procedural room fallback when no GLB available */}
      {!hasRoomGlb && roomData && <ProceduralRoom roomData={roomData} />}

      {/* Contact shadows on the floor (only for procedural room — GLB has own geometry) */}
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
      {placements?.map((p) => (
        <FurnitureModel key={p.item_id} placement={p} item={itemMap.get(p.item_id)} />
      ))}
    </>
  );
}

export function RoomViewer({ roomData, roomGlbUrl, placements, furnitureItems }: RoomViewerProps) {
  const camX = roomData ? roomData.width_m * 1.1 : 8;
  const camY = roomData ? Math.max(roomData.height_m * 1.8, 4) : 6;
  const camZ = roomData ? roomData.length_m * 1.1 : 8;
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        background: "linear-gradient(180deg, #f8f8fc 0%, #ffffff 100%)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Subtle grid overlay for depth */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse at center, transparent 0%, rgba(255,255,255,0.4) 80%)",
          pointerEvents: "none",
          zIndex: 1,
        }}
      />

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
            placements={placements}
            furnitureItems={furnitureItems}
          />
        </Canvas>
      </ViewerErrorBoundary>

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
          background: "rgba(255,255,255,0.8)",
          backdropFilter: "blur(12px)",
          border: "1px solid rgba(26,26,56,0.06)",
          fontSize: "0.6875rem",
          color: "rgba(26,26,56,0.45)",
          letterSpacing: "0.02em",
          zIndex: 2,
          animation: "fadeIn 1s ease-out 0.5s both",
        }}
      >
        <span>Drag to rotate</span>
        <span style={{ opacity: 0.3 }}>|</span>
        <span>Scroll to zoom</span>
        <span style={{ opacity: 0.3 }}>|</span>
        <span>Right-drag to pan</span>
      </div>
    </div>
  );
}
