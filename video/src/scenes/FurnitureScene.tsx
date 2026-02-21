import React, { useMemo, useEffect, useRef } from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Easing,
} from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { useThree } from "@react-three/fiber";
import { Box3, Vector3 } from "three";
import { COLORS, lerp, smoothstep } from "../components/DesignTokens";
import { useGLTFDelayed } from "../three/useGLTFDelayed";
import { loadFont as loadRighteous } from "@remotion/google-fonts/Righteous";

const { fontFamily: displayFont } = loadRighteous();

const FURNITURE = [
  { name: "Sofa", pos: [1.5, 0.4, 2] as const, size: [2, 0.8, 0.9] as const, color: "#d4c8bc" },
  { name: "Coffee Table", pos: [2.5, 0.25, 3] as const, size: [0.8, 0.5, 0.5] as const, color: "#8b7355" },
  { name: "Bookshelf", pos: [4.5, 0.9, 0.3] as const, size: [1.2, 1.8, 0.4] as const, color: "#c4b5a0" },
  { name: "Armchair", pos: [0.5, 0.35, 3.5] as const, size: [0.8, 0.7, 0.8] as const, color: "#a69279" },
  { name: "Floor Lamp", pos: [0.3, 0.75, 1.5] as const, size: [0.3, 1.5, 0.3] as const, color: "#2e2e38" },
];

function SlowPanCamera({ frame, totalFrames }: { frame: number; totalFrames: number }) {
  const { camera } = useThree();
  const lookTarget = useRef(new Vector3());

  useEffect(() => {
    const progress = frame / totalFrames;
    const px = lerp(6.5, 5.0, smoothstep(progress));
    const py = lerp(5.5, 4.0, smoothstep(progress));
    const pz = lerp(8.0, 6.5, smoothstep(progress));
    camera.position.set(px, py, pz);
    lookTarget.current.set(2.5, 0.5, 2.5);
    camera.lookAt(lookTarget.current);
  }, [frame, totalFrames, camera]);

  return null;
}

function FurnitureDrop({
  item,
  startFrame,
  fps,
}: {
  item: (typeof FURNITURE)[0];
  startFrame: number;
  fps: number;
}) {
  const frame = useCurrentFrame();
  const localFrame = frame - startFrame;
  if (localFrame < 0) return null;

  const scale = spring({
    frame: localFrame,
    fps,
    config: { stiffness: 120, damping: 12, mass: 0.8 },
  });
  const dropY = interpolate(localFrame, [0, 10], [3, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <mesh
      position={[item.pos[0], item.pos[1] + dropY, item.pos[2]]}
      scale={[scale, scale, scale]}
      castShadow
      receiveShadow
    >
      <boxGeometry args={[...item.size]} />
      <meshStandardMaterial color={item.color} roughness={0.85} metalness={0.05} />
    </mesh>
  );
}

function RoomModelStatic() {
  const gltf = useGLTFDelayed("demo-room.glb");

  const cloned = useMemo(() => {
    if (!gltf) return null;
    const c = gltf.scene.clone();
    const box = new Box3().setFromObject(c);
    const size = new Vector3();
    box.getSize(size);
    if (size.x > 0.01 && size.z > 0.01) {
      const s = Math.min(5 / size.x, 5 / size.z);
      c.scale.setScalar(s);
      const sb = new Box3().setFromObject(c);
      c.position.y -= sb.min.y;
      c.position.x -= sb.min.x;
      c.position.z -= sb.min.z;
    }
    return c;
  }, [gltf]);

  if (!cloned) return null;

  return <primitive object={cloned} receiveShadow castShadow />;
}

export const FurnitureScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height, fps, durationInFrames } = useVideoConfig();

  const labelOpacity = interpolate(frame, [0, 12], [0, 1], {
    easing: Easing.out(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill>
      <ThreeCanvas
        width={width}
        height={height}
        camera={{ position: [6.5, 5.5, 8], fov: 45 }}
      >
        <color attach="background" args={["#f5f0eb"]} />
        <ambientLight intensity={0.4} color="#f5f0eb" />
        <directionalLight position={[5, 10, 4]} intensity={1.2} castShadow />
        <directionalLight position={[-3, 6, -2]} intensity={0.3} color="#93c5fd" />
        <hemisphereLight intensity={0.3} color="#fef3c7" groundColor="#1e1b4b" />
        <RoomModelStatic />
        <SlowPanCamera frame={frame} totalFrames={durationInFrames} />
        {FURNITURE.map((item, i) => (
          <FurnitureDrop key={item.name} item={item} startFrame={10 + i * 15} fps={fps} />
        ))}
      </ThreeCanvas>

      <div
        style={{
          position: "absolute",
          top: 48,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          opacity: labelOpacity,
        }}
      >
        <div
          style={{
            fontFamily: displayFont,
            fontSize: 24,
            fontWeight: 400,
            color: COLORS.text,
            letterSpacing: "0.03em",
            background: "rgba(250,249,247,0.85)",
            padding: "10px 28px",
            borderRadius: 100,
            boxShadow: "0 4px 24px rgba(26,26,56,0.08)",
          }}
        >
          AI-Placed Furniture
        </div>
      </div>
    </AbsoluteFill>
  );
};
