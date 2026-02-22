import { useState, useEffect } from "react";
import { delayRender, continueRender, staticFile } from "remotion";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import type { GLTF } from "three/examples/jsm/loaders/GLTFLoader.js";

const cache = new Map<string, GLTF>();

export function useGLTFDelayed(filename: string): GLTF | null {
  const url = staticFile(filename);
  const [handle] = useState(() =>
    delayRender("Loading GLB: " + filename, { timeoutInMilliseconds: 120_000 }),
  );
  const [gltf, setGltf] = useState<GLTF | null>(cache.get(url) ?? null);

  useEffect(() => {
    if (cache.has(url)) {
      setGltf(cache.get(url)!);
      continueRender(handle);
      return;
    }

    const loader = new GLTFLoader();
    loader.load(
      url,
      (result) => {
        cache.set(url, result);
        setGltf(result);
        continueRender(handle);
      },
      undefined,
      (error) => {
        console.error("Failed to load GLB:", error);
        continueRender(handle);
      },
    );
  }, [url, handle]);

  return gltf;
}
