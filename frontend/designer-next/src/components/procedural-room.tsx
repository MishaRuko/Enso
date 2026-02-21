"use client";

import { useMemo } from "react";
import * as THREE from "three";
import type { RoomData, DoorWindow } from "@/lib/types";

// --- Constants ---
const WALL_THICKNESS = 0.12;
const DOOR_HEIGHT = 2.1;
const WINDOW_HEIGHT = 1.2;
const WINDOW_SILL = 0.9;

const WALL_COLOR = "#f5f0eb";
const FLOOR_COLOR = "#d4b896";
const CEILING_COLOR = "#faf8f5";

interface ProceduralRoomProps {
  roomData: RoomData;
}

/** Given a wall direction and room dimensions, return the wall length. */
function wallLength(wall: DoorWindow["wall"], room: RoomData): number {
  return wall === "north" || wall === "south" ? room.width_m : room.length_m;
}

/**
 * Build wall segments for one wall, splitting around door/window openings.
 * Each segment is a { start, end, bottomY, topY } in local wall coordinates.
 */
interface WallSegment {
  start: number;
  end: number;
  bottomY: number;
  topY: number;
}

function buildWallSegments(wall: DoorWindow["wall"], room: RoomData): WallSegment[] {
  const len = wallLength(wall, room);
  const h = room.height_m;

  // Collect openings on this wall
  const doors = room.doors.filter((d) => d.wall === wall);
  const windows = room.windows.filter((w) => w.wall === wall);

  // Sort all openings left-to-right along the wall
  type Opening = {
    left: number;
    right: number;
    bottomY: number;
    topY: number;
  };
  const openings: Opening[] = [];

  for (const d of doors) {
    const center = d.position_m;
    const halfW = d.width_m / 2;
    openings.push({
      left: Math.max(0, center - halfW),
      right: Math.min(len, center + halfW),
      bottomY: 0,
      topY: DOOR_HEIGHT,
    });
  }

  for (const w of windows) {
    const center = w.position_m;
    const halfW = w.width_m / 2;
    openings.push({
      left: Math.max(0, center - halfW),
      right: Math.min(len, center + halfW),
      bottomY: WINDOW_SILL,
      topY: WINDOW_SILL + WINDOW_HEIGHT,
    });
  }

  openings.sort((a, b) => a.left - b.left);

  if (openings.length === 0) {
    return [{ start: 0, end: len, bottomY: 0, topY: h }];
  }

  const segments: WallSegment[] = [];

  for (const op of openings) {
    // Full-height segment to the left of the opening
    if (op.left > 0) {
      const prevRight = segments.length > 0 ? segments[segments.length - 1].end : 0;
      if (op.left > prevRight) {
        segments.push({ start: prevRight, end: op.left, bottomY: 0, topY: h });
      }
    }

    // Panel above the opening
    if (op.topY < h) {
      segments.push({
        start: op.left,
        end: op.right,
        bottomY: op.topY,
        topY: h,
      });
    }

    // Panel below the opening (for windows with a sill)
    if (op.bottomY > 0) {
      segments.push({
        start: op.left,
        end: op.right,
        bottomY: 0,
        topY: op.bottomY,
      });
    }
  }

  // Full-height segment to the right of the last opening
  const lastRight = openings[openings.length - 1].right;
  if (lastRight < len) {
    segments.push({ start: lastRight, end: len, bottomY: 0, topY: h });
  }

  return segments;
}

/** Convert a wall-local segment to world position and box dimensions. */
function segmentToWorld(
  seg: WallSegment,
  wall: DoorWindow["wall"],
  room: RoomData,
): { position: [number, number, number]; size: [number, number, number] } {
  const segW = seg.end - seg.start;
  const segH = seg.topY - seg.bottomY;
  const midAlong = (seg.start + seg.end) / 2;
  const midY = (seg.bottomY + seg.topY) / 2;

  switch (wall) {
    case "north":
      // North wall runs along X at Z=0
      return {
        position: [midAlong, midY, 0],
        size: [segW, segH, WALL_THICKNESS],
      };
    case "south":
      // South wall runs along X at Z=length
      return {
        position: [midAlong, midY, room.length_m],
        size: [segW, segH, WALL_THICKNESS],
      };
    case "west":
      // West wall runs along Z at X=0
      return {
        position: [0, midY, midAlong],
        size: [WALL_THICKNESS, segH, segW],
      };
    case "east":
      // East wall runs along Z at X=width
      return {
        position: [room.width_m, midY, midAlong],
        size: [WALL_THICKNESS, segH, segW],
      };
  }
}

export function ProceduralRoom({ roomData }: ProceduralRoomProps) {
  const wallSegments = useMemo(() => {
    const walls: DoorWindow["wall"][] = ["north", "south", "west", "east"];
    const allSegs: {
      position: [number, number, number];
      size: [number, number, number];
      key: string;
    }[] = [];

    for (const wall of walls) {
      const segs = buildWallSegments(wall, roomData);
      for (let i = 0; i < segs.length; i++) {
        const world = segmentToWorld(segs[i], wall, roomData);
        allSegs.push({ ...world, key: `${wall}-${i}` });
      }
    }

    return allSegs;
  }, [roomData]);

  const wallMaterial = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: WALL_COLOR,
        roughness: 0.9,
        side: THREE.DoubleSide,
      }),
    [],
  );

  const floorMaterial = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: FLOOR_COLOR,
        roughness: 0.8,
      }),
    [],
  );

  const ceilingMaterial = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: CEILING_COLOR,
        roughness: 0.95,
        side: THREE.BackSide,
      }),
    [],
  );

  return (
    <group>
      {/* Floor */}
      <mesh
        position={[roomData.width_m / 2, 0, roomData.length_m / 2]}
        rotation={[-Math.PI / 2, 0, 0]}
        receiveShadow
        material={floorMaterial}
      >
        <planeGeometry args={[roomData.width_m, roomData.length_m]} />
      </mesh>

      {/* Ceiling */}
      <mesh
        position={[roomData.width_m / 2, roomData.height_m, roomData.length_m / 2]}
        rotation={[-Math.PI / 2, 0, 0]}
        material={ceilingMaterial}
      >
        <planeGeometry args={[roomData.width_m, roomData.length_m]} />
      </mesh>

      {/* Wall segments */}
      {wallSegments.map((seg) => (
        <mesh
          key={seg.key}
          position={seg.position}
          castShadow
          receiveShadow
          material={wallMaterial}
        >
          <boxGeometry args={seg.size} />
        </mesh>
      ))}
    </group>
  );
}
