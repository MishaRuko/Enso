"use client";

import { Suspense, useEffect, useMemo, useRef, type MutableRefObject } from "react";
import { Canvas, useFrame, useThree, useLoader } from "@react-three/fiber";
import { useGLTF, Environment } from "@react-three/drei";
import type * as THREE from "three";
import { Vector3, Box3, MeshStandardMaterial, Plane } from "three";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import type { DesignSession } from "@/lib/types";
import { FurnitureModel } from "@/components/furniture-model";

/* ── Math helpers ──────────────────────────────────────────────── */

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

function smoothstep(t: number) {
  return t * t * (3 - 2 * t);
}

/* ── Camera waypoints (relative to room center) ────────────────── */

interface Waypoint {
  pos: [number, number, number];
  look: [number, number, number];
}

function computeWaypoints(session: DesignSession): Waypoint[] {
  const room = session.room_data?.rooms?.[0];
  const w = room?.width_m ?? 5;
  const l = room?.length_m ?? 5;
  const h = room?.height_m ?? 2.8;
  const cx = w / 2;
  const cz = l / 2;

  return [
    // 0 — Bird's eye overview
    { pos: [w * 1.5, h * 3.5, l * 1.5], look: [cx, 0, cz] },
    // 1 — Corner view, angled down
    { pos: [w * 1.2, h * 1.5, l * 1.2], look: [cx, h * 0.3, cz] },
    // 2 — Eye-level from one wall
    { pos: [0.3, h * 0.55, cz], look: [w, h * 0.35, cz] },
    // 3 — Low angle from opposite side
    { pos: [cx, h * 0.4, l + 0.5], look: [cx, h * 0.3, 0] },
    // 4 — Pull-back hero shot
    { pos: [w * 1.3, h * 2.2, l * 1.6], look: [cx, 0, cz] },
  ];
}

/* ── Scroll-driven camera ──────────────────────────────────────── */

function ScrollCamera({
  scrollRef,
  waypoints,
}: {
  scrollRef: MutableRefObject<number>;
  waypoints: Waypoint[];
}) {
  const { camera } = useThree();
  const lookTarget = useRef(new Vector3());

  useFrame(() => {
    const totalScroll = document.documentElement.scrollHeight - window.innerHeight;
    if (totalScroll <= 0) return;

    const progress = Math.min(1, Math.max(0, scrollRef.current / totalScroll));
    const segments = waypoints.length - 1;
    const raw = progress * segments;
    const idx = Math.min(Math.floor(raw), segments - 1);
    const t = smoothstep(raw - idx);

    const from = waypoints[idx];
    const to = waypoints[Math.min(idx + 1, segments)];

    camera.position.set(
      lerp(from.pos[0], to.pos[0], t),
      lerp(from.pos[1], to.pos[1], t),
      lerp(from.pos[2], to.pos[2], t),
    );

    lookTarget.current.set(
      lerp(from.look[0], to.look[0], t),
      lerp(from.look[1], to.look[1], t),
      lerp(from.look[2], to.look[2], t),
    );
    camera.lookAt(lookTarget.current);
  });

  return null;
}

/* ── Floor-clip detection (reused from room-viewer) ────────────── */

function detectFloorClipY(root: THREE.Object3D): number | null {
  const ys: number[] = [];
  root.traverse((child) => {
    if ("geometry" in child) {
      const geo = (child as THREE.Mesh).geometry;
      const pos = geo?.attributes?.position;
      if (!pos) return;
      for (let i = 0; i < pos.count; i += 4) ys.push(pos.getY(i));
    }
  });
  if (ys.length < 20) return null;
  ys.sort((a, b) => a - b);

  const box = new Box3().setFromObject(root);
  const totalHeight = box.max.y - box.min.y;
  if (totalHeight < 0.01) return null;

  const bins = 40;
  const binSize = totalHeight / bins;
  const counts = new Array<number>(bins).fill(0);
  for (const y of ys) {
    const idx = Math.min(Math.floor((y - box.min.y) / binSize), bins - 1);
    counts[idx]++;
  }
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
  let belowCount = 0;
  for (let i = 0; i < floorBin; i++) belowCount += counts[i];
  if (belowCount < ys.length * 0.05) return null;
  return box.min.y + floorBin * binSize;
}

/* ── Room model (GLB or OBJ) ───────────────────────────────────── */

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

function RoomOBJ({ url }: { url: string }) {
  const obj = useLoader(OBJLoader, url);
  const cloned = useMemo(() => {
    const c = obj.clone();
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
  return <primitive object={cloned} />;
}

function RoomGLB({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  const cloned = scene.clone();
  applyFloorClip(cloned);
  return <primitive object={cloned} receiveShadow castShadow />;
}

/* ── Scene ─────────────────────────────────────────────────────── */

function ShowcaseScene({
  session,
  scrollRef,
  waypoints,
}: {
  session: DesignSession;
  scrollRef: MutableRefObject<number>;
  waypoints: Waypoint[];
}) {
  const itemMap = new Map(session.furniture_list?.map((i) => [i.id, i]) ?? []);
  const { gl } = useThree();
  gl.localClippingEnabled = true;

  return (
    <>
      <color attach="background" args={["#f5f0eb"]} />
      <ambientLight intensity={0.4} color="#f5f0eb" />
      <directionalLight
        position={[5, 10, 4]}
        intensity={1.2}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
      />
      <directionalLight position={[-3, 6, -2]} intensity={0.3} color="#93c5fd" />
      <hemisphereLight intensity={0.3} color="#fef3c7" groundColor="#1e1b4b" />
      <Environment preset="apartment" />

      <ScrollCamera scrollRef={scrollRef} waypoints={waypoints} />

      {session.room_glb_url && (
        <Suspense fallback={null}>
          {isObjUrl(session.room_glb_url) ? (
            <RoomOBJ url={session.room_glb_url} />
          ) : (
            <RoomGLB url={session.room_glb_url} />
          )}
        </Suspense>
      )}

      {session.placements?.placements?.map((p) => (
        <FurnitureModel key={p.item_id} placement={p} item={itemMap.get(p.item_id)} />
      ))}
    </>
  );
}

/* ── Exported canvas wrapper ───────────────────────────────────── */

export function ShowcaseCanvas({ session }: { session: DesignSession }) {
  const scrollRef = useRef(0);
  const waypoints = useRef(computeWaypoints(session)).current;

  useEffect(() => {
    function onScroll() {
      scrollRef.current = window.scrollY;
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <Canvas
      shadows
      camera={{
        position: waypoints[0].pos,
        fov: 45,
      }}
      gl={{
        antialias: true,
        alpha: false,
        powerPreference: "high-performance",
      }}
      style={{ width: "100%", height: "100%" }}
    >
      <ShowcaseScene session={session} scrollRef={scrollRef} waypoints={waypoints} />
    </Canvas>
  );
}
