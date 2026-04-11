"use client";

export default function ImageLightbox({ src, onClose }: { src: string; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center cursor-zoom-out"
      style={{ background: "rgba(0, 0, 0, 0.85)", backdropFilter: "blur(8px)" }}
      onClick={onClose}
    >
      <button
        onClick={onClose}
        className="absolute top-4 right-4 w-10 h-10 rounded-full flex items-center justify-center text-white text-xl"
        style={{ background: "rgba(255,255,255,0.1)" }}
      >
        &times;
      </button>
      <img
        src={src}
        alt="Expanded slide"
        className="max-w-[90vw] max-h-[90vh] rounded-2xl shadow-2xl"
        style={{ objectFit: "contain", background: "white" }}
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  );
}
