import { useThree } from "@react-three/fiber";
import { Vector3 } from "three";
import { useRef, useEffect } from "react";
import { lerp, smoothstep } from "../components/DesignTokens";

interface Waypoint {
  pos: [number, number, number];
  look: [number, number, number];
}

function computeDefaultWaypoints(): Waypoint[] {
  const w = 5;
  const l = 5;
  const h = 2.8;
  const cx = w / 2;
  const cz = l / 2;

  return [
    { pos: [w * 1.5, h * 3.5, l * 1.5], look: [cx, 0, cz] },
    { pos: [w * 1.2, h * 1.5, l * 1.2], look: [cx, h * 0.3, cz] },
    { pos: [0.3, h * 0.55, cz], look: [w, h * 0.35, cz] },
    { pos: [cx, h * 0.4, l + 0.5], look: [cx, h * 0.3, 0] },
    { pos: [w * 1.3, h * 2.2, l * 1.6], look: [cx, 0, cz] },
  ];
}

interface FlythroughCameraProps {
  frame: number;
  totalFrames: number;
  waypoints?: Waypoint[];
}

export const FlythroughCamera: React.FC<FlythroughCameraProps> = ({
  frame,
  totalFrames,
  waypoints,
}) => {
  const { camera } = useThree();
  const lookTarget = useRef(new Vector3());
  const wps = waypoints ?? computeDefaultWaypoints();

  useEffect(() => {
    const progress = Math.min(1, Math.max(0, frame / totalFrames));
    const segments = wps.length - 1;
    const raw = progress * segments;
    const idx = Math.min(Math.floor(raw), segments - 1);
    const t = smoothstep(raw - idx);

    const from = wps[idx];
    const to = wps[Math.min(idx + 1, segments)];

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
  }, [frame, totalFrames, wps, camera]);

  return null;
};
