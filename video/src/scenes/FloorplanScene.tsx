import React, { useMemo } from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
} from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { Box3, Vector3 } from "three";
import { COLORS } from "../components/DesignTokens";
import { AnimatedText } from "../components/AnimatedText";
import { useGLTFDelayed } from "../three/useGLTFDelayed";
import { loadFont as loadRighteous } from "@remotion/google-fonts/Righteous";
import { loadFont as loadSpaceGrotesk } from "@remotion/google-fonts/SpaceGrotesk";

const { fontFamily: displayFont } = loadRighteous();
const { fontFamily: bodyFont } = loadSpaceGrotesk();

function RoomModelInner({ frame }: { frame: number }) {
  const gltf = useGLTFDelayed("demo-room.glb");

  const computed = useMemo(() => {
    if (!gltf) return null;
    const scene = gltf.scene.clone();
    const box = new Box3().setFromObject(scene);
    const center = box.getCenter(new Vector3());
    const size = box.getSize(new Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const s = 3 / maxDim;
    return {
      scene,
      scale: s,
      offset: new Vector3(-center.x * s, -center.y * s + 0.2, -center.z * s),
    };
  }, [gltf]);

  if (!computed) return null;

  const rotY = frame * 0.006;
  const floatY = Math.sin(frame * 0.04) * 0.04;

  return (
    <group
      scale={[computed.scale, computed.scale, computed.scale]}
      position={[computed.offset.x, computed.offset.y + floatY, computed.offset.z]}
      rotation={[0, rotY, 0]}
    >
      <primitive object={computed.scene} />
    </group>
  );
}

export const FloorplanScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  const floorplanOpacity = interpolate(frame, [0, 8], [0, 1], {
    easing: Easing.out(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <AbsoluteFill
        style={{
          opacity: floorplanOpacity,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 20,
        }}
      >
        <AnimatedText delay={0} duration={10}>
          <div
            style={{
              fontFamily: bodyFont,
              fontSize: 13,
              fontWeight: 600,
              color: COLORS.accent,
              letterSpacing: "0.16em",
              textTransform: "uppercase" as const,
            }}
          >
            Upload Your Floorplan
          </div>
        </AnimatedText>
        <AnimatedText delay={3} duration={10}>
          <svg width={400} height={300} viewBox="0 0 400 300" fill="none">
            <rect x={40} y={30} width={320} height={240} stroke={COLORS.text} strokeWidth={2} fill="rgba(236,230,219,0.2)" rx={4} />
            <line x1={200} y1={30} x2={200} y2={180} stroke={COLORS.text} strokeWidth={1.5} />
            <line x1={200} y1={180} x2={360} y2={180} stroke={COLORS.text} strokeWidth={1.5} />
            <path d="M 200 170 A 30 30 0 0 1 170 180" stroke={COLORS.textMuted} strokeWidth={1} fill="none" />
            <line x1={40} y1={100} x2={40} y2={160} stroke={COLORS.accent} strokeWidth={3} />
            <line x1={280} y1={270} x2={340} y2={270} stroke={COLORS.accent} strokeWidth={3} />
            <text x={110} y={140} fontFamily={bodyFont} fontSize={14} fill={COLORS.textMuted} textAnchor="middle">Living Room</text>
            <text x={280} y={120} fontFamily={bodyFont} fontSize={12} fill={COLORS.textMuted} textAnchor="middle">Kitchen</text>
            <text x={200} y={20} fontFamily={bodyFont} fontSize={11} fill={COLORS.textSecondary} textAnchor="middle">8.0 m</text>
          </svg>
        </AnimatedText>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
