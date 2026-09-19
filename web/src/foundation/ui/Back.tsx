"use client";
import { useRouter } from "next/navigation";
import React from "react";
import { GoArrowLeft } from "react-icons/go";
function Back() {
  const router = useRouter();
  return (
    <div>
      {" "}
      <button
        onClick={() => router.back()}
        className="inline-flex items-center text-b2c-text-secondary hover:text-osce-ink-900 mb-8 group"
      >
        {" "}
        <GoArrowLeft className="h-5 w-5 mr-2 group-hover:-translate-x-1 transition-transform" />{" "}
        <span>Back</span>{" "}
      </button>{" "}
    </div>
  );
}
export default Back;
