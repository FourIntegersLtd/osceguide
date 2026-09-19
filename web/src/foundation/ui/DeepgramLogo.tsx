import React from "react";

function DeepgramLogo() {
  return (
    <div className="relative flex h-8 w-8 items-center justify-center rounded-sm bg-black">
      <div
        className="absolute inset-0 h-[32px] w-[18px] bg-white"
        style={{
          clipPath: 'path("M 18 0 L 0 0 L 0 32 L 18 32 C 8 32 8 0 18 0")',
        }}
      />
    </div>
  );
}

export default DeepgramLogo;
