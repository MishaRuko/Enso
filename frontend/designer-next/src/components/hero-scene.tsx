"use client";

import { useRef, useState, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useGLTF, Float } from "@react-three/drei";
import type * as THREE from "three";
import { Box3, Vector3 } from "three";

/* ── Preload the demo room GLB so it's cached before the Canvas mounts ── */
const DEMO_ROOM_URL = "/demo-room.glb";
useGLTF.preload(DEMO_ROOM_URL);

/* ── Room model that drifts right on scroll ────────────────────── */

function RoomModel({ scrollRef }: { scrollRef: React.MutableRefObject<number> }) {
  const { scene } = useGLTF(DEMO_ROOM_URL);
  const groupRef = useRef<THREE.Group>(null);

  // Center and scale the model on first mount
  useEffect(() => {
    if (!groupRef.current) return;
    const box = new Box3().setFromObject(scene);
    const center = box.getCenter(new Vector3());
    const size = box.getSize(new Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const scale = 3 / maxDim; // fit into ~3 unit radius
    const scaledWidth = size.x * scale;
    groupRef.current.scale.setScalar(scale);
    // Offset right by ~60% of the scaled width so the model sits in the right half
    groupRef.current.position.set(-center.x * scale + scaledWidth * 0.6, -center.y * scale + 0.2, -center.z * scale);
  }, [scene]);

  useFrame((_state, delta) => {
    if (!groupRef.current) return;
    // Slow constant rotation
    groupRef.current.rotation.y += delta * 0.08;
    // Drift right based on scroll
    const baseX = groupRef.current.userData.baseX ?? groupRef.current.position.x;
    groupRef.current.userData.baseX = baseX;
    groupRef.current.position.x = baseX + scrollRef.current * 5;
  });

  return (
    <Float speed={0.6} rotationIntensity={0.03} floatIntensity={0.2}>
      <group ref={groupRef}>
        <primitive object={scene} />
      </group>
    </Float>
  );
}

/* ── Warm lighting (no Environment HDR — zero network) ─────────── */

function Scene({ scrollRef }: { scrollRef: React.MutableRefObject<number> }) {
  const { gl } = useThree();
  gl.localClippingEnabled = true;

  return (
    <>
      <ambientLight intensity={0.6} color="#faf9f7" />
      <directionalLight
        position={[6, 10, 5]}
        intensity={1.2}
        color="#fff5ee"
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
      />
      <directionalLight position={[-4, 6, -3]} intensity={0.35} color="#93c5fd" />
      <hemisphereLight intensity={0.35} color="#fef3c7" groundColor="#2e2e38" />

      <RoomModel scrollRef={scrollRef} />
    </>
  );
}

/* ── Exported component ────────────────────────────────────────── */

interface HeroSceneProps {
  scrollProgress: number;
}

export function HeroScene({ scrollProgress }: HeroSceneProps) {
  const scrollRef = useRef(scrollProgress);
  scrollRef.current = scrollProgress;

  // SSR guard — Canvas needs WebGL
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;

  return (
    <div style={{ position: "absolute", inset: 0, zIndex: 0 }}>
      <Canvas
        shadows
        camera={{ position: [1.8, 2.5, 5.5], fov: 40 }}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        style={{ width: "100%", height: "100%" }}
        dpr={[1, 1.5]}
      >
        <Scene scrollRef={scrollRef} />
      </Canvas>
    </div>
  );
}
