import React, { useMemo, useRef, useEffect } from "react";
import { useGLTF } from "@react-three/drei";
import { staticFile } from "remotion";
import { Box3, Vector3 } from "three";
import type * as THREE from "three";

const ROOM_URL = staticFile("demo-room.glb");

interface RoomModelProps {
  frame: number;
  rotationSpeed?: number;
  driftX?: number;
}

export const RoomModel: React.FC<RoomModelProps> = ({
  frame,
  rotationSpeed = 0.002,
  driftX = 0,
}) => {
  const { scene } = useGLTF(ROOM_URL);
  const groupRef = useRef<THREE.Group>(null);

  const { scale, offset, scaledWidth } = useMemo(() => {
    const box = new Box3().setFromObject(scene);
    const center = box.getCenter(new Vector3());
    const size = box.getSize(new Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const s = 3 / maxDim;
    return {
      scale: s,
      offset: new Vector3(
        -center.x * s,
        -center.y * s + 0.2,
        -center.z * s,
      ),
      scaledWidth: size.x * s,
    };
  }, [scene]);

  const rotationY = frame * rotationSpeed;
  const floatY = Math.sin(frame * 0.03) * 0.05;
  const posX = offset.x + scaledWidth * 0.6 + driftX;

  return (
    <group
      ref={groupRef}
      scale={[scale, scale, scale]}
      position={[posX, offset.y + floatY, offset.z]}
      rotation={[0, rotationY, 0]}
    >
      <primitive object={scene} />
    </group>
  );
};

useGLTF.preload(ROOM_URL);
