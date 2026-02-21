import React from "react";

export const RoomLighting: React.FC = () => (
  <>
    <ambientLight intensity={0.6} color="#faf9f7" />
    <directionalLight
      position={[6, 10, 5]}
      intensity={1.2}
      color="#fff5ee"
      castShadow
      shadow-mapSize-width={2048}
      shadow-mapSize-height={2048}
      shadow-bias={-0.001}
    />
    <directionalLight position={[-4, 6, -3]} intensity={0.35} color="#93c5fd" />
    <hemisphereLight intensity={0.35} color="#fef3c7" groundColor="#2e2e38" />
  </>
);
