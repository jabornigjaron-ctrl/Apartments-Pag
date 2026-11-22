import React from "react";
import { Composition } from "remotion";
import { Reel, ReelProps, reelDuration, FPS } from "./Reel";

const beispiel: ReelProps = {
  template: "kinetic",
  transition: "mix",
  clips: [
    { src: "videos/strand-036.mp4", start: 1, dur: 2.5 },
    { src: "videos/strand-050.mp4", start: 1, dur: 2.5 },
    { src: "videos/apartments-003.mp4", start: 6, dur: 4 },
  ],
  hook: { kicker: "Speicher dir das", text: "3 Gründe für *Pag* 2027" },
  items: [{ from: 2.5, to: 5, text: "Türkises *Wasser*" }],
  end: { kicker: "traumurlaub-pag.com", text: "Sommer 2027 *anfragen*", cta: "Link in Bio" },
  music: "musik/house-1.m4a",
  bpm: 122,
  location: "Gajac · Insel Pag",
};

export const Root: React.FC = () => (
  <Composition
    id="Reel"
    component={Reel}
    width={1080}
    height={1920}
    fps={FPS}
    durationInFrames={reelDuration(beispiel)}
    defaultProps={beispiel}
    calculateMetadata={({ props }) => ({ durationInFrames: reelDuration(props as ReelProps) })}
  />
);
