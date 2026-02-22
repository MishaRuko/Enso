import React, { useMemo, useEffect, useRef } from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { useThree } from "@react-three/fiber";
import { Box3, Vector3 } from "three";
import { COLORS, lerp, smoothstep } from "../components/DesignTokens";
import { useGLTFDelayed } from "../three/useGLTFDelayed";
import { loadFont as loadRighteous } from "@remotion/google-fonts/Righteous";

const { fontFamily: displayFont } = loadRighteous();

interface Waypoint {
  pos: [number, number, number];
  look: [number, number, number];
}

const WAYPOINTS: Waypoint[] = [
  { pos: [5.5, 6.0, 5.5], look: [2.0, 0.5, 2.0] },
  { pos: [4.5, 3.5, 4.5], look: [2.0, 0.8, 2.0] },
  { pos: [0.5, 1.8, 2.5], look: [3.5, 0.8, 2.0] },
  { pos: [2.5, 1.5, 5.0], look: [2.0, 0.6, 0.5] },
  { pos: [5.0, 4.5, 5.5], look: [2.0, 0.3, 2.0] },
];

function CameraController({
  frame,
  totalFrames,
}: {
  frame: number;
  totalFrames: number;
}) {
  const { camera } = useThree();
  const lookTarget = useRef(new Vector3());

  useEffect(() => {
    const progress = Math.min(1, Math.max(0, frame / totalFrames));
    const segments = WAYPOINTS.length - 1;
    const raw = progress * segments;
    const idx = Math.min(Math.floor(raw), segments - 1);
    const t = smoothstep(raw - idx);

    const from = WAYPOINTS[idx];
    const to = WAYPOINTS[Math.min(idx + 1, segments)];

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
  }, [frame, totalFrames, camera]);

  return null;
}

function RoomModelStatic() {
  const gltf = useGLTFDelayed("furnished-room.glb");

  const cloned = useMemo(() => {
    if (!gltf) return null;
    const c = gltf.scene.clone();
    const box = new Box3().setFromObject(c);
    const size = new Vector3();
    box.getSize(size);
    if (size.x > 0.01 && size.z > 0.01) {
      const scale = Math.min(5 / size.x, 5 / size.z);
      c.scale.setScalar(scale);
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

export const FlythroughScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height, durationInFrames } = useVideoConfig();

  const labelOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill>
      <ThreeCanvas
        width={width}
        height={height}
        camera={{ position: WAYPOINTS[0].pos, fov: 45 }}
      >
        <color attach="background" args={["#f5f0eb"]} />
        <ambientLight intensity={0.4} color="#f5f0eb" />
        <directionalLight
          position={[5, 10, 4]}
          intensity={1.2}
          castShadow
        />
        <directionalLight position={[-3, 6, -2]} intensity={0.3} color="#93c5fd" />
        <hemisphereLight intensity={0.3} color="#fef3c7" groundColor="#1e1b4b" />
        <RoomModelStatic />
        <CameraController frame={frame} totalFrames={durationInFrames} />
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
          Explore Your Room
        </div>
      </div>
    </AbsoluteFill>
  );
};
