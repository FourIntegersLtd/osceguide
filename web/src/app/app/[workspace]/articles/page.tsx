import { redirect } from "next/navigation";

/** Articles are the public /blogs pages now. */
export default function Page() {
  redirect("/blogs");
}
