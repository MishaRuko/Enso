"use client";

import { Component, Suspense, useMemo, type ReactNode } from "react";
import { useGLTF } from "@react-three/drei";
import { Box3, Vector3 } from "three";
import type { FurnitureItem, FurniturePlacement } from "@/lib/types";

interface FurnitureModelInnerProps {
  url: string;
  placement: FurniturePlacement;
  item?: FurnitureItem;
}

function isIkeaGlb(item?: FurnitureItem): boolean {
  const url = item?.glb_url ?? "";
  return url.includes("ikea.com") || url.includes("ikea-static");
}

function GLBModel({ url, placement, item }: FurnitureModelInnerProps) {
  const { scene } = useGLTF(url);

  const cloned = useMemo(() => {
    const c = scene.clone();
    const box = new Box3().setFromObject(c);
    const size = new Vector3();
    box.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z);

    if (maxDim < 0.001) return c;

    // IKEA GLBs (dimma/assets) are already in metres — skip rescaling.
    // Only rescale non-IKEA models (e.g. fal.ai TRELLIS) using known dimensions.
    if (!isIkeaGlb(item) && item?.dimensions) {
      const expectedW = item.dimensions.width_cm / 100;
      const expectedD = item.dimensions.depth_cm / 100;
      const expectedH = item.dimensions.height_cm / 100;
      const maxExpected = Math.max(expectedW, expectedD, expectedH);
      const scale = maxExpected / maxDim;
      c.scale.setScalar(scale);
    }

    // Position bottom at y=0
    const scaledBox = new Box3().setFromObject(c);
    c.position.y -= scaledBox.min.y;
    // Center horizontally on origin so placement position is the center
    const center = new Vector3();
    scaledBox.getCenter(center);
    c.position.x -= center.x;
    c.position.z -= center.z;

    return c;
  }, [scene, item]);

  return (
    <primitive
      object={cloned}
      position={[placement.position.x, placement.position.y, placement.position.z]}
      rotation={[0, (placement.rotation_y_degrees * Math.PI) / 180, 0]}
      castShadow
      receiveShadow
    />
  );
}

interface PlaceholderBoxProps {
  placement: FurniturePlacement;
  item?: FurnitureItem;
}

function PlaceholderBox({ placement, item }: PlaceholderBoxProps) {
  const w = item?.dimensions ? item.dimensions.width_cm / 100 : 0.5;
  const h = item?.dimensions ? item.dimensions.height_cm / 100 : 0.5;
  const d = item?.dimensions ? item.dimensions.depth_cm / 100 : 0.5;

  return (
    <mesh
      position={[placement.position.x, placement.position.y + h / 2, placement.position.z]}
      rotation={[0, (placement.rotation_y_degrees * Math.PI) / 180, 0]}
      castShadow
    >
      <boxGeometry args={[w, h, d]} />
      <meshStandardMaterial color="#2e2e38" transparent opacity={0.35} />
    </mesh>
  );
}

// Error boundary to catch GLB loading failures (CORS, 404, etc.)
class GLBErrorBoundary extends Component<
  { fallback: ReactNode; children: ReactNode },
  { hasError: boolean }
> {
  constructor(props: { fallback: ReactNode; children: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  componentDidCatch(error: Error) {
    console.warn("GLB load failed:", error.message);
  }
  render() {
    if (this.state.hasError) return this.props.fallback;
    return this.props.children;
  }
}

interface FurnitureModelProps {
  placement: FurniturePlacement;
  item?: FurnitureItem;
}

function proxyGlbUrl(url: string): string {
  if (url.includes("ikea.com") || url.includes("ikea-static")) {
    return `/api/proxy-glb?url=${encodeURIComponent(url)}`;
  }
  return url;
}

export function FurnitureModel({ placement, item }: FurnitureModelProps) {
  const rawUrl = item?.glb_url;
  const glbUrl = rawUrl ? proxyGlbUrl(rawUrl) : undefined;

  if (!glbUrl) {
    return <PlaceholderBox placement={placement} item={item} />;
  }

  const fallback = <PlaceholderBox placement={placement} item={item} />;

  return (
    <GLBErrorBoundary fallback={fallback}>
      <Suspense fallback={fallback}>
        <GLBModel url={glbUrl} placement={placement} item={item} />
      </Suspense>
    </GLBErrorBoundary>
  );
}
