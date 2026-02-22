import React, { useMemo, useEffect, useRef } from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
} from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { useThree } from "@react-three/fiber";
import { Box3, Vector3 } from "three";
import { COLORS, lerp, smoothstep } from "../components/DesignTokens";
import { useGLTFDelayed } from "../three/useGLTFDelayed";
import { loadFont as loadRighteous } from "@remotion/google-fonts/Righteous";

const { fontFamily: displayFont } = loadRighteous();

function SlowPanCamera({ frame, totalFrames }: { frame: number; totalFrames: number }) {
  const { camera } = useThree();
  const lookTarget = useRef(new Vector3());

  useEffect(() => {
    const progress = frame / totalFrames;
    const t = smoothstep(progress);
    // Start from where FlythroughScene's camera ends, then smoothly pan out
    const px = lerp(5.0, 5.0, t);
    const py = lerp(4.5, 4.0, t);
    const pz = lerp(5.5, 6.5, t);
    camera.position.set(px, py, pz);
    lookTarget.current.set(
      lerp(2.0, 2.5, t),
      lerp(0.3, 0.5, t),
      lerp(2.0, 2.5, t),
    );
    camera.lookAt(lookTarget.current);
  }, [frame, totalFrames, camera]);

  return null;
}

function FurnishedRoomModel() {
  const gltf = useGLTFDelayed("furnished-room.glb");

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
        camera={{ position: [5.0, 4.5, 5.5], fov: 45 }}
      >
        <color attach="background" args={["#f5f0eb"]} />
        <ambientLight intensity={0.4} color="#f5f0eb" />
        <directionalLight position={[5, 10, 4]} intensity={1.2} castShadow />
        <directionalLight position={[-3, 6, -2]} intensity={0.3} color="#93c5fd" />
        <hemisphereLight intensity={0.3} color="#fef3c7" groundColor="#1e1b4b" />
        <FurnishedRoomModel />
        <SlowPanCamera frame={frame} totalFrames={durationInFrames} />
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
