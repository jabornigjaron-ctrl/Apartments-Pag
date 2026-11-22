import React, { useEffect, useState } from "react";
import {
  AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, continueRender, delayRender,
  interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Easing,
} from "remotion";

export const FPS = 30;

// ---------------------------------------------------------------- Typen
export type Clip = { src: string; start?: number; dur: number; focus?: number };
export type Item = { from: number; to: number; text: string };
export type ReelProps = {
  template: "kinetic" | "pov" | "elegant";
  transition: "cut" | "fade" | "slide" | "zoom" | "mix";
  clips: Clip[];
  hook?: { kicker?: string; text: string; sek?: number };
  items?: Item[];
  end?: { kicker?: string; text: string; cta?: string; sek?: number };
  music?: string;
  bpm?: number;
  location?: string;
  accent?: string;
};

const OV = 12; // Ueberblend-Frames (0,4 s)
const ov = (p: ReelProps) => (p.transition === "cut" ? 0 : OV);
export const reelDuration = (p: ReelProps) =>
  Math.max(1, Math.round(p.clips.reduce((s, c) => s + c.dur * FPS, 0) - ov(p) * (p.clips.length - 1)));

const ACCENT = "#FFD84D";
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// ---------------------------------------------------------------- Schriften
const FONTS: [string, string][] = [
  ["Anton", "fonts/Anton-Regular.ttf"],
  ["MontserratXB", "fonts/Montserrat-ExtraBold.ttf"],
  ["MontserratSB", "fonts/Montserrat-SemiBold.ttf"],
  ["Playfair", "fonts/PlayfairDisplay-MediumItalic.ttf"],
  ["Caveat", "fonts/Caveat-Bold.ttf"],
];
const useFonts = () => {
  const [handle] = useState(() => delayRender("Schriften laden"));
  useEffect(() => {
    Promise.all(FONTS.map(([name, file]) => {
      const f = new FontFace(name, `url(${staticFile(file)})`);
      return f.load().then((l) => { (document as any).fonts.add(l); });
    })).then(() => continueRender(handle)).catch(() => continueRender(handle));
  }, [handle]);
};

// "Text mit *Hervorhebung*" -> [{w, hi}]
const words = (text: string) => {
  const out: { w: string; hi: boolean }[] = [];
  text.split(/(\*[^*]+\*)/).forEach((part) => {
    const hi = part.startsWith("*") && part.endsWith("*");
    part.replace(/\*/g, "").split(/\s+/).filter(Boolean).forEach((w) => out.push({ w, hi }));
  });
  return out;
};

const shadow = "0 6px 28px rgba(0,0,0,0.45), 0 2px 6px rgba(0,0,0,0.35)";

// ---------------------------------------------------------------- Clips
const ClipView: React.FC<{ clip: Clip; enter: string; durF: number; bpm?: number; punch: boolean; globalFrom: number }> =
  ({ clip, enter, durF, bpm, punch, globalFrom }) => {
    const f = useCurrentFrame();
    const g = f + globalFrom;
    let scale = interpolate(f, [0, durF], [1.04, 1.12]);
    if (punch && bpm) {
      const bf = (60 / bpm) * FPS;
      const ph = (g % bf) / bf;
      scale += 0.035 * Math.exp(-ph * 7);
    }
    let opacity = 1, tx = 0, blur = 0, extra = 1;
    const p = interpolate(f, [0, OV], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
    if (enter === "fade") opacity = p;
    if (enter === "slide") tx = (1 - p) * 1080;
    if (enter === "zoom") { extra = interpolate(p, [0, 1], [1.35, 1]); opacity = p; }
    if (enter === "whip") { tx = (1 - p) * -1080; blur = (1 - p) * 30; }
    const style: React.CSSProperties = {
      width: "100%", height: "100%", objectFit: "cover",
      objectPosition: `${(clip.focus ?? 0.5) * 100}% 50%`,
    };
    const isImg = /\.(jpe?g|png)$/i.test(clip.src);
    return (
      <AbsoluteFill style={{ opacity, transform: `translateX(${tx}px)`, filter: blur ? `blur(${blur}px)` : undefined }}>
        <AbsoluteFill style={{ transform: `scale(${scale * extra})` }}>
          {isImg ? <Img src={staticFile(clip.src)} style={style} /> :
            <OffthreadVideo src={staticFile(clip.src)} startFrom={Math.round((clip.start ?? 0) * FPS)} muted style={style} />}
        </AbsoluteFill>
      </AbsoluteFill>
    );
  };

// ---------------------------------------------------------------- Text-Bausteine
const Kicker: React.FC<{ text: string; f: number; dark?: boolean; serif?: boolean }> = ({ text, f, dark, serif }) => {
  const { fps } = useVideoConfig();
  const s = spring({ frame: f, fps, config: { damping: 16, stiffness: 160 } });
  return (
    <div style={{
      display: "inline-block", padding: serif ? "0" : "12px 28px", borderRadius: 999,
      background: serif ? "transparent" : dark ? "rgba(0,0,0,0.35)" : "rgba(255,255,255,0.18)",
      border: serif ? "none" : "1.5px solid rgba(255,255,255,0.45)", backdropFilter: "blur(10px)",
      fontFamily: "MontserratSB", fontSize: serif ? 30 : 30, letterSpacing: serif ? "0.38em" : "0.22em",
      textTransform: "uppercase", color: "white", textShadow: serif ? shadow : undefined,
      opacity: s, transform: `translateY(${(1 - s) * -24}px)`,
    }}>{text}</div>
  );
};

const KineticText: React.FC<{ text: string; f: number; size: number; accent: string }> = ({ text, f, size, accent }) => {
  const { fps } = useVideoConfig();
  return (
    <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: `${size * 0.12}px ${size * 0.22}px`, padding: "0 70px" }}>
      {words(text).map(({ w, hi }, i) => {
        const s = spring({ frame: f + 5 - i * 2, fps, config: { damping: 11, stiffness: 190, mass: 0.7 } });
        return (
          <span key={i} style={{
            fontFamily: "Anton", fontSize: size, lineHeight: 1.05, textTransform: "uppercase",
            color: hi ? "#111" : "white", background: hi ? accent : "transparent",
            padding: hi ? `0 ${size * 0.14}px` : 0, borderRadius: 14,
            textShadow: hi ? "none" : shadow, WebkitTextStroke: hi ? undefined : "2px rgba(0,0,0,0.35)",
            boxShadow: hi ? "0 10px 30px rgba(0,0,0,0.35)" : undefined,
            display: "inline-block", opacity: Math.min(1, s * 1.4),
            transform: `translateY(${(1 - s) * 50}px) scale(${0.5 + 0.5 * s}) rotate(${hi ? -2 : 0}deg)`,
          }}>{w}</span>
        );
      })}
    </div>
  );
};

const PovText: React.FC<{ text: string; f: number; size: number }> = ({ text, f, size }) => {
  const plain = text.replace(/\*/g, "");
  const n = Math.floor(interpolate(f, [0, plain.length * 1.2], [0, plain.length], clamp));
  const lines = plain.slice(0, Math.max(1, n)).split("|");
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
      {lines.map((l, i) => (
        <div key={i} style={{
          background: "rgba(255,255,255,0.97)", color: "#111", fontFamily: "MontserratSB", fontSize: size,
          padding: "14px 26px", borderRadius: 22, boxShadow: "0 8px 24px rgba(0,0,0,0.25)", lineHeight: 1.15,
        }}>{l}</div>
      ))}
    </div>
  );
};

const ElegantText: React.FC<{ text: string; f: number; size: number }> = ({ text, f, size }) => {
  const lines = text.replace(/\*/g, "").split("|");
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      {lines.map((l, i) => {
        const p = interpolate(f - 6 - i * 6, [0, 22], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
        return (
          <div key={i} style={{ overflow: "hidden", padding: "0 20px" }}>
            <div style={{
              fontFamily: "Playfair", fontSize: size, color: "white", lineHeight: 1.18, textShadow: shadow,
              transform: `translateY(${(1 - p) * 100}%)`, opacity: p,
            }}>{l}</div>
          </div>
        );
      })}
      <div style={{
        height: 3, marginTop: 26, background: "rgba(255,255,255,0.85)",
        width: interpolate(f, [10, 40], [0, 220], { ...clamp, easing: Easing.out(Easing.cubic) }),
      }} />
    </div>
  );
};

// Ein Textblock mit Ein-/Ausblenden zwischen from..to (Frames)
const Block: React.FC<{ from: number; to: number; top: number; children: (f: number) => React.ReactNode }> =
  ({ from, to, top, children }) => {
    const frame = useCurrentFrame();
    if (frame < from || frame > to) return null;
    const f = frame - from;
    const out = interpolate(frame, [to - 8, to], [1, 0], clamp);
    return (
      <AbsoluteFill style={{ top, height: "auto", alignItems: "center", opacity: out, transform: `scale(${0.96 + 0.04 * out})` }}>
        {children(f)}
      </AbsoluteFill>
    );
  };

const ListCard: React.FC<{ n: number; text: string; f: number; accent: string; template: string }> = ({ n, text, f, accent, template }) => {
  const { fps } = useVideoConfig();
  const s = spring({ frame: f, fps, config: { damping: 14, stiffness: 170 } });
  const plain = text.replace(/^\s*\d+\.\s*/, "");
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 26, padding: "22px 36px 22px 22px", margin: "0 60px",
      borderRadius: 28, background: template === "pov" ? "rgba(255,255,255,0.96)" : "rgba(0,0,0,0.38)",
      backdropFilter: "blur(14px)", border: "1.5px solid rgba(255,255,255,0.25)",
      transform: `translateX(${(1 - s) * -700}px)`, opacity: s,
    }}>
      <div style={{
        minWidth: 86, height: 86, borderRadius: 999, background: accent, color: "#111",
        display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Anton", fontSize: 54,
      }}>{n}</div>
      <div style={{ fontFamily: "MontserratXB", fontSize: 58, color: template === "pov" ? "#111" : "white", lineHeight: 1.1 }}>
        {words(plain).map(({ w, hi }, i) => (
          <span key={i} style={{ color: hi ? (template === "pov" ? "#E8A600" : accent) : undefined }}>{w} </span>
        ))}
      </div>
    </div>
  );
};

const LocationPin: React.FC<{ text: string; from: number }> = ({ text, from }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - from;
  if (f < 0 || f > 110) return null;
  const s = spring({ frame: f, fps, config: { damping: 12, stiffness: 200 } });
  const out = interpolate(f, [100, 110], [1, 0], clamp);
  return (
    <AbsoluteFill>
      <div style={{
        position: "absolute", top: 1330, left: 60,
        display: "inline-flex", alignItems: "center", gap: 14, padding: "14px 26px 14px 18px", borderRadius: 999,
        background: "rgba(255,255,255,0.95)", boxShadow: "0 10px 30px rgba(0,0,0,0.3)",
        transform: `scale(${s})`, transformOrigin: "left center", opacity: out,
        fontFamily: "MontserratXB", fontSize: 36, color: "#111",
      }}>
        <svg width="40" height="40" viewBox="0 0 24 24"><path fill="#E5484D" d="M12 2a7 7 0 0 0-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>
        {text}
      </div>
    </AbsoluteFill>
  );
};

const Cta: React.FC<{ text: string; f: number; accent: string; light: boolean }> = ({ text, f, accent, light }) => {
  const { fps } = useVideoConfig();
  const s = spring({ frame: f - 10, fps, config: { damping: 10, stiffness: 180 } });
  const pulse = 1 + 0.04 * Math.sin((f / fps) * Math.PI * 2 * 1.2);
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 18, marginTop: 40 }}>
      <div style={{
        padding: "22px 46px", borderRadius: 999, background: light ? "white" : accent, color: "#111",
        fontFamily: "MontserratXB", fontSize: 44, boxShadow: "0 12px 34px rgba(0,0,0,0.35)",
        transform: `scale(${s * pulse})`,
      }}>{text} →</div>
      <div style={{ fontFamily: "MontserratSB", fontSize: 32, color: "white", textShadow: shadow, opacity: s }}>@traumurlaub_pag</div>
    </div>
  );
};

const ProgressBar: React.FC<{ total: number }> = ({ total }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ top: 70, left: 60, right: 60, height: 8, width: "auto", borderRadius: 8, background: "rgba(255,255,255,0.3)" }}>
      <div style={{ width: `${(frame / total) * 100}%`, height: "100%", borderRadius: 8, background: "white" }} />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- Reel
export const Reel: React.FC<ReelProps> = (p) => {
  useFonts();
  const total = reelDuration(p);
  const accent = p.accent || ACCENT;
  const o = ov(p);
  const kinds = ["fade", "slide", "zoom", "whip"];

  let cursor = 0;
  const seqs = p.clips.map((c, i) => {
    const durF = Math.round(c.dur * FPS);
    const from = cursor;
    cursor += durF - o;
    const enter = i === 0 || p.transition === "cut" ? "none" : p.transition === "mix" ? kinds[(i * 7 + 3) % 4] : p.transition;
    return { c, from, durF, enter };
  });

  const T = (s: number) => Math.round(s * FPS);
  const hookEnd = T(p.hook?.sek ?? (p.template === "kinetic" ? 2.8 : 4));
  const endStart = total - T(p.end?.sek ?? 3.5);

  const renderText = (text: string, f: number, kind: "hook" | "end") => {
    if (p.template === "kinetic") return <KineticText text={text} f={f} size={kind === "hook" ? 128 : 108} accent={accent} />;
    if (p.template === "pov") return <PovText text={text} f={f} size={56} />;
    return <ElegantText text={text} f={f} size={kind === "hook" ? 104 : 92} />;
  };

  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {seqs.map(({ c, from, durF, enter }, i) => (
        <Sequence key={i} from={from} durationInFrames={durF}>
          <ClipView clip={c} enter={enter} durF={durF} bpm={p.bpm} punch={p.template === "kinetic"} globalFrom={from} />
        </Sequence>
      ))}
      {/* leichter Verlauf oben/unten fuer Lesbarkeit */}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.35) 0%, rgba(0,0,0,0) 30%, rgba(0,0,0,0) 62%, rgba(0,0,0,0.35) 100%)" }} />

      {p.items?.length ? <ProgressBar total={total} /> : null}

      {p.hook && (
        <Block from={0} to={hookEnd} top={p.template === "elegant" ? 330 : 380}>
          {(f) => (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 26 }}>
              {p.hook!.kicker && (p.template === "pov"
                ? <div style={{ fontFamily: "MontserratXB", fontSize: 40, color: "white", textShadow: shadow }}>{p.hook!.kicker}</div>
                : <Kicker text={p.hook!.kicker} f={f} serif={p.template === "elegant"} />)}
              {renderText(p.hook!.text, f, "hook")}
            </div>
          )}
        </Block>
      )}

      {(p.items || []).map((it, i) => (
        <Block key={i} from={T(it.from)} to={T(it.to)} top={1040}>
          {(f) => <ListCard n={i + 1} text={it.text} f={f} accent={accent} template={p.template} />}
        </Block>
      ))}

      {p.location && <LocationPin text={p.location} from={T(0.8)} />}

      {p.end && (
        <Block from={endStart} to={total} top={p.template === "elegant" ? 640 : 560}>
          {(f) => (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 26 }}>
              {p.end!.kicker && <Kicker text={p.end!.kicker} f={f} serif={p.template === "elegant"} dark />}
              {renderText(p.end!.text, f, "end")}
              {p.end!.cta && <Cta text={p.end!.cta} f={f} accent={accent} light={p.template !== "kinetic"} />}
            </div>
          )}
        </Block>
      )}

      {p.music && (
        <Audio src={staticFile(p.music)}
          volume={(f) => interpolate(f, [0, 6, total - 40, total], [0, 1, 1, 0], clamp)} />
      )}
    </AbsoluteFill>
  );
};
