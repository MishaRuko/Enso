import React from "react";
import { Composition } from "remotion";
import { EnsoPromo } from "./EnsoPromo";
import { FPS, totalCompositionFrames } from "./beat-map";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="EnsoPromo"
        component={EnsoPromo}
        durationInFrames={totalCompositionFrames()}
        fps={FPS}
        width={1920}
        height={1080}
      />
    </>
  );
};
