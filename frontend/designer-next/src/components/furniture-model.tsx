"use client";

import { Component, Suspense, type ReactNode } from "react";
import { useGLTF } from "@react-three/drei";
import type { FurnitureItem, FurniturePlacement } from "@/lib/types";

interface FurnitureModelInnerProps {
  url: string;
  placement: FurniturePlacement;
}

function GLBModel({ url, placement }: FurnitureModelInnerProps) {
  const { scene } = useGLTF(url);

  return (
    <primitive
      object={scene.clone()}
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
  // Use item dimensions if available, otherwise default 50cm cube
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
      <meshStandardMaterial color="#1a1a38" transparent opacity={0.15} />
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

export function FurnitureModel({ placement, item }: FurnitureModelProps) {
  const glbUrl = item?.glb_url;

  if (!glbUrl) {
    return <PlaceholderBox placement={placement} item={item} />;
  }

  const fallback = <PlaceholderBox placement={placement} item={item} />;

  return (
    <GLBErrorBoundary fallback={fallback}>
      <Suspense fallback={fallback}>
        <GLBModel url={glbUrl} placement={placement} />
      </Suspense>
    </GLBErrorBoundary>
  );
}
